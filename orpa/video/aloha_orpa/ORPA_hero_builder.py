#!/usr/bin/env python3
"""Create the ORPA comparative research hero with a Low Camera picture-in-picture.

- Main view: High Camera.
- Inset view: Low Camera, bottom-left just ABOVE the lower-third label bar, without a label.
- Low Camera inset rotation: 90 degrees clockwise by default; configurable with --low-rotation.
- Rollout labels: green Success / red Failure accents, as previously approved.
- Full-screen opening, chapter and closing cards: #2d3748 background, white Helvetica text, no lines.
- Opening card: full research title, four authors, and AIST affiliation.
- Closing card: exact two-line research claim, held longer.
- Total duration: 35 seconds at 30 FPS.
- Success episode: 0 for both Snack Box Transfer and Chip Tube Opening.
- Object Sorting: Baseline ACT failure, episode 3.

Usage:
  python ORPA_hero_builder.py --input inputs --map rollout_map.json \\
    --out output/orpa_hero_comparative.mp4 \\
    --snack-failure-episode 2 --chip-failure-episode 3 --repair-map

Requires Python 3.8+, FFmpeg (with fontconfig), ffprobe, and DejaVu Sans for rollout labels.
Helvetica must be installed for an exact match; otherwise fontconfig selects a substitute.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 30
WIDTH = 1920
HEIGHT = 1080

# Only for full-screen opening, task transitions, and closing.
# Rollout footage, bottom labels and camera inset use their existing styling.
TRANSITION_BG = "0x2d3748"
TRANSITION_FONT = "Helvetica"

TASK_DIRS = {
    "snack_box_transfer": "orpa_snack_box_transfer",
    "chip_tube_opening": "orpa_chip_tube_opening",
    "object_sorting": "orpa_object_sorting",
}

CAMERA_SUFFIX = {
    "high": "high_camera",
    "low": "low_camera",
    "left_wrist": "left_wrist_camera",
    "right_wrist": "right_wrist_camera",
}

# Durations in seconds. Total: exactly 35.0s at 30 FPS.
# Opening is slightly longer to accommodate the full research title and authors.
# Closing holds longer (4.8s vs. the previous 2.8s).
SEQUENCE = [
    ("opening", 3.6),
    ("card", "SNACK BOX TRANSFER", "REAL-WORLD MANIPULATION", 3.2),
    ("roll", "snack_failure", 0.0, 3.0, "Snack Box Transfer", "Baseline ACT", "Failure"),
    ("roll", "snack_success", 3.0, 4.0, "Snack Box Transfer", "ACT + ORPA", "Success"),
    ("card", "CHIP TUBE OPENING", "REAL-WORLD MANIPULATION", 3.2),
    ("roll", "chip_failure", 0.0, 3.0, "Chip Tube Opening", "Baseline ACT", "Failure"),
    ("roll", "chip_success", 3.0, 4.0, "Chip Tube Opening", "ACT + ORPA", "Success"),
    ("card", "OBJECT SORTING", "BASELINE ACT FAILURE CASE", 3.2),
    ("roll", "object_failure", 0.0, 3.0, "Object Sorting", "Baseline ACT", "Failure"),
    ("card", "ORPA: ONLINE RESIDUAL POLICY ADAPTATION",
     "NO BASE POLICY TRAINING • NO FK–IK ROUND TRIP", 4.8),
]


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        print("[FFMPEG ERROR]", file=sys.stderr)
        print(" ".join(str(x) for x in cmd), file=sys.stderr)
        print(proc.stderr[-7500:], file=sys.stderr)
        raise RuntimeError("FFmpeg command failed")


def esc(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("%", "\\%")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def font_file():
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).is_file():
            return path
    raise RuntimeError("Font missing. Try: sudo apt install fonts-dejavu-core")


def probe(path):
    val = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True)
    return float(val.strip())


def card_filter(title, subtitle, font, width, height):
    scale = height / 1080
    # Wider text gets a slightly smaller font so the exact closing copy fits.
    title_size = round((62 if len(title) > 30 else 78) * scale)
    subtitle_size = round((38 if len(subtitle) > 38 else 34) * scale)
    offset1 = round(72 * scale)
    offset2 = round(45 * scale)
    return (
        f"drawtext=font='{esc(TRANSITION_FONT)}':text='{esc(title)}':fontcolor=white:"
        f"fontsize={title_size}:x=(w-text_w)/2:y=h/2-{offset1},"
        f"drawtext=font='{esc(TRANSITION_FONT)}':text='{esc(subtitle)}':fontcolor=white:"
        f"fontsize={subtitle_size}:x=(w-text_w)/2:y=h/2+{offset2}"
    )


def opening_filter(font, width, height):
    """Full research title (wrapped for legibility), authors, and affiliation.

    Only white Helvetica text on a #2d3748 background; no decorative lines or boxes.
    """
    scale = height / 1080.0
    lines = [
        ("ORPA: Online Residual Policy Adaptation", 74, 242),
        ("for Robot Manipulation Control with Human Feedback", 55, 340),
        ("Muhammad A. Muttaqien   Tomohiro Motoda   Ryo Hanai   Yukiyasu Domae", 35, 580),
        ("Embodied AI Research Team, National Institute of AIST, Tokyo, Japan", 32, 679),
    ]
    return ",".join(
        f"drawtext=font='{esc(TRANSITION_FONT)}':text='{esc(text)}':"
        f"fontcolor=white:fontsize={max(9,round(size*scale))}:"
        f"x=(w-text_w)/2:y={round(y*scale)}"
        for text, size, y in lines
    )


def render_opening(output, seconds, font, width, height, quick):
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c={TRANSITION_BG}:s={width}x{height}:r={FPS}:d={seconds}",
        "-vf", opening_filter(font, width, height),
        "-an", "-c:v", "libx264", "-preset", "ultrafast" if quick else "fast",
        "-crf", "27" if quick else "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-frames:v", str(round(seconds * FPS)), str(output),
    ])


def render_card(output, title, subtitle, seconds, font, width, height, quick):
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c={TRANSITION_BG}:s={width}x{height}:r={FPS}:d={seconds}",
        "-vf", card_filter(title, subtitle, font, width, height),
        "-an", "-c:v", "libx264", "-preset", "ultrafast" if quick else "fast",
        "-crf", "27" if quick else "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-frames:v", str(round(seconds * FPS)), str(output),
    ])


def create_roll_filter(start, seconds, title, method, outcome, font, width, height, low_rotation):
    # The two inputs are synchronized by trimming to the same start/duration.
    scale = height / 1080
    fg_w = int(round(height * 4 / 3 / 2) * 2)
    bar_h = round(116 * scale)
    left = round(70 * scale)
    marker = max(6, round(18 * scale))
    label_font = round(42 * scale)

    # Low Camera inset sits above the lower-third. No camera-name text or inset header.
    # Rotated 90/270 degrees = portrait. Keep the original view and its aspect ratio;
    # do NOT stretch or crop the Low Camera footage to fill a landscape inset.
    if low_rotation in (90, 270):
        pip_h = int(round(376 * scale / 2) * 2)
        pip_w = int(round(pip_h * 3 / 4 / 2) * 2)
    else:
        pip_w = int(round(376 * scale / 2) * 2)
        pip_h = int(round(pip_w * 3 / 4 / 2) * 2)
    pip_x = round(65 * scale)
    pip_y = height - bar_h - pip_h - round(26 * scale)
    pip_border = max(2, round(3 * scale))

    rotation_filter = {0: "", 90: "transpose=clock,", 180: "hflip,vflip,",
                       270: "transpose=cclock,"}[low_rotation]

    accent = "#22c55e" if outcome.lower() == "success" else "#ef6464"
    left_text = f"{title}  |  {method}"
    bar_top = height - bar_h
    bar_mid = height - bar_h / 2

    return (
        f"[0:v]trim=start={start}:duration={seconds},setpts=PTS-STARTPTS,"
        f"fps={FPS},format=yuv420p,split=2[bgsource][fgsource];"
        f"[bgsource]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=18:8[bg];"
        f"[fgsource]scale={fg_w}:{height}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[canvas];"
        f"[1:v]trim=start={start}:duration={seconds},setpts=PTS-STARTPTS,"
        f"fps={FPS},{rotation_filter}scale={pip_w}:{pip_h},format=yuv420p,"
        f"drawbox=x=0:y=0:w={pip_w}:h={pip_h}:color=white@0.90:t={pip_border}[pip];"
        f"[canvas][pip]overlay={pip_x}:{pip_y}:shortest=1[withpip];"
        f"[withpip]drawbox=x=0:y={bar_top}:w={width}:h={bar_h}:color=black@0.68:t=fill,"
        f"drawbox=x={left}:y={bar_mid}-{marker}/2:w={marker}:h={marker}:color={accent}:t=fill,"
        f"drawtext=fontfile='{esc(font)}':text='{esc(left_text)}':"
        f"fontcolor=white:fontsize={label_font}:x={left + marker + round(19*scale)}:"
        f"y={bar_mid}-text_h/2,"
        f"drawtext=fontfile='{esc(font)}':text='{outcome.upper()}':"
        f"fontcolor={accent}:fontsize={label_font}:x=w-text_w-{left}:"
        f"y={bar_mid}-text_h/2[outv]"
    )


def render_roll(output, high, low, start, seconds, title, method, outcome, font,
                width, height, quick, low_rotation):
    for path in {high, low}:
        duration = probe(path)
        if start + seconds > duration + 0.04:
            raise ValueError(f"{path} is {duration:.2f}s, needs {start + seconds:.2f}s")

    filt = create_roll_filter(start, seconds, title, method, outcome, font, width, height, low_rotation)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(high), "-i", str(low),
        "-filter_complex", filt, "-map", "[outv]", "-an", "-c:v", "libx264",
        "-preset", "ultrafast" if quick else "fast", "-crf", "27" if quick else "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-frames:v", str(round(seconds * FPS)), str(output),
    ])


def select_failure(mapping, task, explicit=None):
    failures = [int(ep) for ep in mapping[task]["act_failures"] if int(ep) != 0]
    if explicit is not None:
        if explicit not in failures:
            raise ValueError(f"{task}: episode {explicit} not in failures {failures}")
        return explicit
    if not failures:
        raise ValueError(f"{task}: no failure episodes specified")
    return failures[0]


def build_sources(input_root, mapping, snack_failure, chip_failure):
    ids = {
        "snack_failure": ("snack_box_transfer", select_failure(mapping, "snack_box_transfer", snack_failure)),
        "snack_success": ("snack_box_transfer", 0),
        "chip_failure": ("chip_tube_opening", select_failure(mapping, "chip_tube_opening", chip_failure)),
        "chip_success": ("chip_tube_opening", 0),
        "object_failure": ("object_sorting", select_failure(mapping, "object_sorting")),
    }
    sources = {}
    for role, (task, ep) in ids.items():
        folder = input_root / TASK_DIRS[task]
        high = folder / f"episode_{ep}_video_{CAMERA_SUFFIX['high']}.mp4"
        low = folder / f"episode_{ep}_video_{CAMERA_SUFFIX['low']}.mp4"
        if not high.is_file():
            raise FileNotFoundError(f"High Camera not found: {high}")
        if not low.is_file():
            raise FileNotFoundError(f"Low Camera not found: {low}")
        sources[role] = (high, low)
        print(f"[SOURCE] {role}: episode {ep} | main={high.name} | inset={low.name}")
    return sources


def main():
    parser = argparse.ArgumentParser(
        description="ORPA research hero with High Camera main view and unlabeled Low Camera inset"
    )
    parser.add_argument("--input", required=True, help="Root inputs folder")
    parser.add_argument("--map", required=True, help="rollout_map.json")
    parser.add_argument("--out", required=True, help="Output MP4 file")
    parser.add_argument("--snack-failure-episode", type=int)
    parser.add_argument("--chip-failure-episode", type=int)
    parser.add_argument("--repair-map", action="store_true",
                        help="Save correct success=0, failures=[1,2,3] mapping to JSON")
    parser.add_argument("--low-rotation", type=int, choices=(0, 90, 180, 270), default=90,
                        help="Rotate Low Camera inset clockwise by these degrees (default: 90)")
    parser.add_argument("--test-small", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required. Install: sudo apt install ffmpeg")
    map_path = Path(args.map)
    if not map_path.is_file():
        raise FileNotFoundError(str(map_path))
    mapping = json.loads(map_path.read_text(encoding="utf-8"))

    for task in ("snack_box_transfer", "chip_tube_opening"):
        if mapping[task].get("act_orpa_success") != 0 or mapping[task].get("act_failures") != [1, 2, 3]:
            print(f"[WARN] correcting stale mapping in memory for {task}")
        mapping[task]["act_orpa_success"] = 0
        mapping[task]["act_failures"] = [1, 2, 3]
    if args.repair_map:
        map_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
        print(f"[SAVED] corrected mapping: {map_path}")

    print(f"[STYLE] Main: High Camera | inset: Low Camera rotated {args.low_rotation}° clockwise (no label)")
    sources = build_sources(
        Path(args.input), mapping, args.snack_failure_episode, args.chip_failure_episode,
    )
    font = font_file()  # Unchanged font for rollout labels.
    if shutil.which("fc-match"):
        try:
            resolved = subprocess.check_output(
                ["fc-match", "-f", "%{family}\n", TRANSITION_FONT], text=True
            ).strip().splitlines()[0]
            print(f"[STYLE] Transition cards: #{TRANSITION_BG[2:]} | requested {TRANSITION_FONT} | resolved {resolved}")
        except (OSError, subprocess.CalledProcessError, IndexError):
            print(f"[STYLE] Transition cards: #{TRANSITION_BG[2:]} | requested {TRANSITION_FONT}")
    width, height = (640, 360) if args.test_small else (WIDTH, HEIGHT)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    total = 0.0
    with tempfile.TemporaryDirectory(prefix="orpa_hero_pip_") as temporary:
        work = Path(temporary)
        parts = []
        for idx, scene in enumerate(SEQUENCE, 1):
            part = work / f"{idx:02d}.mp4"
            if scene[0] == "opening":
                _, duration = scene
                render_opening(part, duration, font, width, height, args.test_small)
            elif scene[0] == "card":
                _, title, subtitle, duration = scene
                render_card(part, title, subtitle, duration, font, width, height, args.test_small)
            else:
                _, role, start, duration, title, method, outcome = scene
                high_path, low_path = sources[role]
                render_roll(part, high_path, low_path, start, duration,
                            title, method, outcome, font, width, height, args.test_small,
                            args.low_rotation)
            total += duration
            parts.append(part)
            print(f"[RENDERED] {idx}/{len(SEQUENCE)}: {scene[0]} · {duration:.1f}s", flush=True)

        manifest = work / "concat.txt"
        manifest.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", "-movflags", "+faststart", str(out),
        ])
    duration = probe(out)
    if abs(duration - total) > 0.12:
        raise RuntimeError(f"Duration mismatch: expected {total:.2f}s, got {duration:.2f}s")
    print(f"[DONE] {out} | {width}x{height} | {duration:.2f}s | {FPS} FPS")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.CalledProcessError) as e:
        sys.exit(f"[ERROR] {e}")
