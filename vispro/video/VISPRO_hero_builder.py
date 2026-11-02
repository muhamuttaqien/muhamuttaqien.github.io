#!/usr/bin/env python3
"""
VISPRO hero builder
-------------------
Builds a 35-second silent MP4 hero video from the six VisPro MP4 clips.

Timeline
  0.0–3.5s   Opening overlay
  3.5–8.0s   Problem overlay
  8.0–14.0s  3x2 successful grid + method statement
 14.0–32.0s  Six individual examples (3.0s each)
 32.0–35.0s  Closing overlay

Input can be either:
  - a zip file (e.g. vispro.zip)
  - a directory that contains the six MP4 files somewhere inside it

Expected filenames:
  trajectory1.mp4 trajectory2.mp4 trajectory3.mp4
  grasping1.mp4   grasping2.mp4   grasping3.mp4

Examples
  python VISPRO_hero_builder.py --input vispro.zip --out vispro_hero.mp4
  python VISPRO_hero_builder.py --input . --out vispro_hero.mp4
  python VISPRO_hero_builder.py --input . --out vispro_preview.mp4 --preview
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

FPS = 30
BACKGROUND = "0x2d3748"
START_OFFSET = 0.6

OPENING_SECONDS = 3.5
PROBLEM_SECONDS = 4.5
GRID_SECONDS = 6.0
INDIVIDUAL_SECONDS = 3.0
CLOSING_SECONDS = 3.0

REQUIRED = [
    "trajectory1.mp4",
    "trajectory2.mp4",
    "trajectory3.mp4",
    "grasping1.mp4",
    "grasping2.mp4",
    "grasping3.mp4",
]

INDIVIDUAL_SEQUENCE = [
    ("trajectory1.mp4", "TRAJECTORY • Choco Box (Rigid cardboard box)"),
    ("trajectory2.mp4", "TRAJECTORY • Choco Box (Rigid cardboard box)"),
    ("trajectory3.mp4", "TRAJECTORY • Choco Box (Rigid cardboard box)"),
    ("grasping1.mp4",  "GRASPING • Choco Box (Rigid cardboard box)"),
    ("grasping2.mp4",  "GRASPING • Tea Bottle (Reflective plastic bottle)"),
    ("grasping3.mp4",  "GRASPING • Small Jars (Slippery cylindrical containers)"),
]


def run(cmd):
    result = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr[-6000:], file=sys.stderr)
        raise RuntimeError("Command failed: " + " ".join(map(str, cmd)))
    return result.stdout


def ff_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def video_duration(path):
    out = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ])
    return float(out.strip())


def find_font(requested=None):
    if requested:
        p = Path(requested).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError("Font file not found: " + str(p))
        return str(p)

    if shutil.which("fc-match"):
        for family in ("Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"):
            try:
                font = run(["fc-match", "-f", "%{file}", family]).strip()
                if font and Path(font).is_file():
                    return font
            except Exception:
                pass

    for candidate in (
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(candidate).is_file():
            return candidate

    raise RuntimeError("No usable font found. Pass --font /path/to/font.ttf")


def write_text_file(workdir, stem, text):
    path = workdir / f"{stem}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def drawtext_file(font, textfile, fontsize, x, y, extra=""):
    parts = [
        f"drawtext=fontfile='{ff_escape(font)}'",
        f"textfile='{ff_escape(textfile)}'",
        "fontcolor=white",
        f"fontsize={fontsize}",
        f"x={x}",
        f"y={y}",
    ]
    if extra:
        parts.append(extra)
    return ":".join(parts)


def output_options(output, frames, preset, crf):
    return [
        "-an",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-frames:v", str(frames),
        "-movflags", "+faststart",
        str(output),
    ]


def recursive_find(root, filename):
    matches = sorted(p for p in root.rglob(filename) if p.is_file())
    return matches[0] if matches else None


def resolve_sources(source, workdir):
    found = {}

    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                name = Path(member.filename).name
                if name in REQUIRED and name not in found:
                    out = workdir / name
                    with zf.open(member) as src, out.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    found[name] = out
    elif source.is_dir():
        for name in REQUIRED:
            match = recursive_find(source, name)
            if match:
                found[name] = match.resolve()
    else:
        raise FileNotFoundError("Input must be an existing .zip file or directory: " + str(source))

    missing = [name for name in REQUIRED if name not in found]
    if missing:
        raise FileNotFoundError("Missing MP4 files: " + ", ".join(missing))

    min_needed = max(START_OFFSET + GRID_SECONDS, START_OFFSET + INDIVIDUAL_SECONDS)
    for name, path in found.items():
        dur = video_duration(path)
        if dur < min_needed - 0.05:
            raise ValueError(f"{name} is too short ({dur:.2f}s). Need at least {min_needed:.2f}s.")

    return found


def render_opening(output, workdir, font, width, height, preset, crf):
    scale = height / 1080.0
    lines = [
        ("Visual Prompting for Robotic Manipulation", 74, 242),
        ("with Annotation-Guided Pick-and-Place Using ACT", 55, 340),
        ("Muhammad A. Muttaqien   Tomohiro Motoda   Ryo Hanai   Yukiyasu Domae", 35, 580),
        ("Embodied AI Research Team, National Institute of AIST, Tokyo, Japan", 32, 679),
    ]

    filters = []
    for i, (text, size, yref) in enumerate(lines):
        txt = write_text_file(workdir, f"opening_{i}", text)
        filters.append(drawtext_file(
            font, txt, max(10, round(size * scale)),
            "(w-text_w)/2", round(yref * scale)
        ))

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", f"color=c={BACKGROUND}:s={width}x{height}:r={FPS}:d={OPENING_SECONDS}",
        "-vf", ",".join(filters),
        *output_options(output, round(OPENING_SECONDS * FPS), preset, crf),
    ])


def render_centered_card(output, workdir, font, width, height, duration, lines, preset, crf,
                         top_heading=None):
    scale = height / 720.0
    filters = []

    if top_heading:
        heading_file = write_text_file(workdir, output.stem + "_heading", top_heading)
        filters.append(drawtext_file(
            font, heading_file, max(18, round(28 * scale)),
            "(w-text_w)/2", round(110 * scale)
        ))

    gap = round(54 * scale)
    start_y = round((height - gap * (len(lines) - 1)) / 2 - 30 * scale)
    for i, line in enumerate(lines):
        txt = write_text_file(workdir, f"{output.stem}_{i}", line)
        filters.append(drawtext_file(
            font, txt, max(16, round(28 * scale)),
            "(w-text_w)/2", start_y + i * gap,
            extra="line_spacing=10"
        ))

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", f"color=c={BACKGROUND}:s={width}x{height}:r={FPS}:d={duration}",
        "-vf", ",".join(filters),
        *output_options(output, round(duration * FPS), preset, crf),
    ])


def render_grid(output, files, workdir, font, width, height, preset, crf):
    # Even dimensions keep YUV420 chroma planes aligned.
    # Explicitly fill the grid gaps to avoid the green edge artifacts
    # that FFmpeg xstack can produce with uninitialized empty pixels.
    cell = max(2, round(height * 0.34) // 2 * 2)
    gap = max(2, round(height * 0.025) // 2 * 2)
    grid_w = cell * 3 + gap * 2
    grid_h = cell * 2 + gap
    grid_x = (width - grid_w) // 2
    grid_y = round(height * 0.075)
    method_h = height - (grid_y + grid_h) - round(height * 0.045)
    method_y = height - method_h

    row1_file = write_text_file(workdir, "grid_row1", "SUCCESSFUL\n(TRAJECTORY)")
    row2_file = write_text_file(workdir, "grid_row2", "SUCCESSFUL\n(GRASPING)")
    method1_file = write_text_file(workdir, "grid_method1", "This method enables robots to interpret and act upon visual cues")
    method2_file = write_text_file(workdir, "grid_method2", "(bounding boxes) efficiently.")

    fc = []
    for idx, name in enumerate(["trajectory1.mp4", "trajectory2.mp4", "trajectory3.mp4",
                                "grasping1.mp4", "grasping2.mp4", "grasping3.mp4"]):
        fc.append(
            f"[{idx}:v]trim=start={START_OFFSET}:duration={GRID_SECONDS},"
            f"setpts=PTS-STARTPTS,fps={FPS},"
            f"scale={cell}:{cell}:force_original_aspect_ratio=decrease,"
            f"pad={cell}:{cell}:(ow-iw)/2:(oh-ih)/2:black[v{idx}]"
        )

    layout = "|".join([
        f"0_0",
        f"{cell + gap}_0",
        f"{2 * (cell + gap)}_0",
        f"0_{cell + gap}",
        f"{cell + gap}_{cell + gap}",
        f"{2 * (cell + gap)}_{cell + gap}",
    ])

    fc.append(
        "[v0][v1][v2][v3][v4][v5]"
        "xstack=inputs=6:layout=%s:fill=%s[stack]" % (layout, BACKGROUND)
    )
    fc.append(f"[6:v][stack]overlay={grid_x}:{grid_y}[b0]")
    fc.append(f"[b0]drawbox=x=0:y={method_y}:w={width}:h={method_h}:color=black@0.68:t=fill[b1]")
    # Center the two-line status labels in the *left gutter* of the grid.
    # This avoids placing text over the robot footage.
    fc.append("[b1]%s[b2]" % drawtext_file(
        font, row1_file, max(14, round(height * 0.030)),
        f"({grid_x}-text_w)/2", f"{grid_y}+({cell}-text_h)/2",
        extra=f"line_spacing={max(2, round(height * 0.012))}"
    ))
    fc.append("[b2]%s[b3]" % drawtext_file(
        font, row2_file, max(14, round(height * 0.030)),
        f"({grid_x}-text_w)/2", f"{grid_y + cell + gap}+({cell}-text_h)/2",
        extra=f"line_spacing={max(2, round(height * 0.012))}"
    ))
    fc.append("[b3]%s[b4]" % drawtext_file(
        font, method1_file, max(14, round(height * 0.030)),
        "(w-text_w)/2", method_y + round(method_h * 0.26)
    ))
    fc.append("[b4]%s[out]" % drawtext_file(
        font, method2_file, max(14, round(height * 0.030)),
        "(w-text_w)/2", method_y + round(method_h * 0.58)
    ))

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for name in ["trajectory1.mp4", "trajectory2.mp4", "trajectory3.mp4",
                 "grasping1.mp4", "grasping2.mp4", "grasping3.mp4"]:
        cmd += ["-i", str(files[name])]
    cmd += [
        "-f", "lavfi", "-i", f"color=c={BACKGROUND}:s={width}x{height}:r={FPS}:d={GRID_SECONDS}",
        "-filter_complex", ";".join(fc),
        "-map", "[out]",
        *output_options(output, round(GRID_SECONDS * FPS), preset, crf),
    ]
    run(cmd)


def render_individual(output, video, label, workdir, font, width, height, preset, crf):
    scale = height / 720.0
    frame_size = round(height * 0.78) // 2 * 2
    bar_h = round(height * 0.12)
    label_file = write_text_file(workdir, output.stem + "_label", label)

    graph = (
        f"[0:v]trim=start={START_OFFSET}:duration={INDIVIDUAL_SECONDS},"
        f"setpts=PTS-STARTPTS,fps={FPS},format=yuv420p,split[blur][sharp];"
        f"[blur]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=22:5,eq=brightness=-0.18[bg];"
        f"[sharp]scale={frame_size}:{frame_size}:force_original_aspect_ratio=decrease,"
        f"pad={frame_size}:{frame_size}:(ow-iw)/2:(oh-ih)/2:black[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[tmp];"
        f"[tmp]drawbox=x=0:y={height - bar_h}:w={width}:h={bar_h}:color=black@0.76:t=fill[tmp2];"
        f"[tmp2]{drawtext_file(font, label_file, max(14, round(29 * scale)), '(w-text_w)/2', f'{height - bar_h}+({bar_h}-text_h)/2')}[out]"
    )

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-filter_complex", graph,
        "-map", "[out]",
        *output_options(output, round(INDIVIDUAL_SECONDS * FPS), preset, crf),
    ])


def render_closing(output, workdir, font, width, height, preset, crf):
    """Match the ORPA hero's two-line closing typography and placement exactly.

    ORPA card_filter() uses 62px for long titles, 38px for long subtitles
    at 1920x1080; both scale by output height / 1080. It places them at
    y=h/2-72*scale and y=h/2+45*scale, respectively.
    """
    scale = height / 1080.0
    title = "Visual Prompting for Robotic Manipulation"
    subtitle = "with Annotation-Guided Pick-and-Place Using ACT"

    title_size = round((62 if len(title) > 30 else 78) * scale)
    subtitle_size = round((38 if len(subtitle) > 38 else 34) * scale)
    title_y = f"h/2-{round(72 * scale)}"
    subtitle_y = f"h/2+{round(45 * scale)}"

    title_file = write_text_file(workdir, "closing_title", title)
    subtitle_file = write_text_file(workdir, "closing_subtitle", subtitle)
    filters = [
        drawtext_file(font, title_file, title_size, "(w-text_w)/2", title_y),
        drawtext_file(font, subtitle_file, subtitle_size, "(w-text_w)/2", subtitle_y),
    ]
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", f"color=c={BACKGROUND}:s={width}x{height}:r={FPS}:d={CLOSING_SECONDS}",
        "-vf", ",".join(filters),
        *output_options(output, round(CLOSING_SECONDS * FPS), preset, crf),
    ])


def main():
    parser = argparse.ArgumentParser(description="Create a 35-second VISPRO hero video")
    parser.add_argument("--input", default="vispro.zip", help="Input zip file or directory")
    parser.add_argument("--out", default="vispro_hero.mp4", help="Output mp4 file")
    parser.add_argument("--font", default=None, help="Optional explicit TTF font file")
    parser.add_argument("--preview", action="store_true", help="Render a quick 640x360 preview")
    parser.add_argument("--preset", default="medium", choices=["ultrafast", "veryfast", "fast", "medium", "slow"])
    parser.add_argument("--crf", type=int, default=22)
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        parser.error("ffmpeg and ffprobe must be installed and available on PATH")
    if not (0 <= args.crf <= 51):
        parser.error("--crf must be between 0 and 51")

    width, height = (640, 360) if args.preview else (1280, 720)
    preset = "ultrafast" if args.preview else args.preset
    crf = 27 if args.preview else args.crf

    source = Path(args.input).expanduser().resolve()
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    font = find_font(args.font)

    total = OPENING_SECONDS + PROBLEM_SECONDS + GRID_SECONDS + len(INDIVIDUAL_SEQUENCE) * INDIVIDUAL_SECONDS + CLOSING_SECONDS
    if abs(total - 35.0) > 1e-6:
        raise RuntimeError(f"Timeline is {total:.3f}s, expected 35.0s")

    with tempfile.TemporaryDirectory(prefix="vispro_hero_") as tmp:
        workdir = Path(tmp)
        files = resolve_sources(source, workdir)
        segments = []

        p = workdir / "segment_00_opening.mp4"
        print("[1/10] opening", flush=True)
        render_opening(p, workdir, font, width, height, preset, crf)
        segments.append(p)

        p = workdir / "segment_01_problem.mp4"
        print("[2/10] problem overlay", flush=True)
        render_centered_card(
            p, workdir, font, width, height, PROBLEM_SECONDS,
            lines=[
                "Robotic pick-and-place tasks in convenience stores pose challenges",
                "due to dense object arrangements, occlusions, and variations in",
                "object properties such as color, shape, size, and texture.",
            ],
            preset=preset, crf=crf, top_heading="Problem"
        )
        segments.append(p)

        p = workdir / "segment_02_grid.mp4"
        print("[3/10] 3x2 successful grid", flush=True)
        render_grid(p, files, workdir, font, width, height, preset, crf)
        segments.append(p)

        for idx, (name, label) in enumerate(INDIVIDUAL_SEQUENCE, start=3):
            p = workdir / f"segment_{idx:02d}_{Path(name).stem}.mp4"
            print(f"[{idx + 1}/10] {name}", flush=True)
            render_individual(p, files[name], label, workdir, font, width, height, preset, crf)
            segments.append(p)

        p = workdir / "segment_09_closing.mp4"
        print("[10/10] closing", flush=True)
        render_closing(p, workdir, font, width, height, preset, crf)
        segments.append(p)

        manifest = workdir / "segments.txt"
        manifest.write_text(
            "".join(f"file '{seg.as_posix()}'\n" for seg in segments),
            encoding="utf-8",
        )

        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", "-movflags", "+faststart", str(output),
        ])

    final_duration = video_duration(output)
    print(f"Created: {output}")
    print(f"Video: {width}x{height} · {FPS} FPS · {final_duration:.2f} seconds")


if __name__ == "__main__":
    main()
