#!/usr/bin/env python3
"""Build the Object Sorting four-camera montage using the ORPA website style.

The known Object Sorting episode 3 is a Baseline ACT failure. This script
preserves the requested output filename but does not claim the rollout is
an ACT + ORPA failure. Camera names are shown; no method/outcome label is added.

Requires Python 3.8+, FFmpeg with libx264 and drawtext, and fontconfig.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

CAMERAS = (
    ("high", "High Camera"),
    ("low", "Low Camera"),
    ("left_wrist", "Left Wrist"),
    ("right_wrist", "Right Wrist"),
)
SLATE = "0x2d3748"
FPS_DEFAULT = 30


def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg command failed:\n" + result.stderr[-5000:])
    return result.stdout


def quote_ffmpeg(value):
    return str(value).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def font_file():
    if shutil.which("fc-match"):
        font = run(["fc-match", "-f", "%{file}", "Helvetica"]).strip()
        if Path(font).is_file():
            return font
    for candidate in (
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("Helvetica-compatible font not found; install fontconfig and a sans-serif font")


def duration_seconds(path):
    data = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json", str(path)
    ]))
    if not data.get("streams"):
        raise ValueError("No video stream in " + str(path))
    stream = data["streams"][0]
    if int(stream.get("width", 0)) <= 0 or int(stream.get("height", 0)) <= 0:
        raise ValueError("Invalid video resolution in " + str(path))
    return float(data["format"]["duration"])


def create_filter(font, fps, duration):
    filters = []
    for index, (camera, label) in enumerate(CAMERAS):
        # Keep the same 640x480 panels and bottom camera tags as ORPA_video_builder.py.
        # Preserve each camera's original orientation without rotation.
        filters.append(
            "[{i}:v]fps={fps},scale=640:480:force_original_aspect_ratio=decrease,"
            "pad=640:480:(ow-iw)/2:(oh-ih)/2:color={slate},setsar=1,"
            "drawbox=x=0:y=ih-46:w=iw:h=46:color={slate}@0.85:t=fill,"
            "drawtext=fontfile='{font}':text='{label}':fontsize=23:"
            "fontcolor=white:x=18:y=h-46+(46-text_h)/2[v{i}]".format(
                i=index, fps=fps, slate=SLATE,
                font=quote_ffmpeg(font), label=quote_ffmpeg(label))
        )
    filters.extend([
        "color=c={}:s=1280x960:r={}:d={:.4f}[bg]".format(SLATE, fps, duration),
        "[bg][v0]overlay=0:0:shortest=1[t0]",
        "[t0][v1]overlay=640:0:shortest=1[t1]",
        "[t1][v2]overlay=0:480:shortest=1[t2]",
        "[t2][v3]overlay=640:480:shortest=1[outv]",
    ])
    return ";".join(filters)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("inputs"), help="Root inputs directory")
    parser.add_argument("--episode", type=int, default=3, help="Object Sorting episode (default: 3)")
    parser.add_argument("--out", type=Path, default=Path("output/object_sorting_act_orpa_failure_multicamera.mp4"))
    parser.add_argument("--fps", type=int, default=FPS_DEFAULT, choices=(24, 25, 30, 50))
    args = parser.parse_args()

    if args.episode < 0:
        raise ValueError("Episode number must be nonnegative")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required: sudo apt install ffmpeg")

    folder = args.input / "orpa_object_sorting"
    files = [folder / "episode_{}_video_{}_camera.mp4".format(args.episode, camera)
             for camera, _ in CAMERAS]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError("Missing source MP4: " + str(path))
    durations = [duration_seconds(path) for path in files]
    duration = min(durations)
    if duration < 0.2:
        raise ValueError("Camera recordings are too short")

    # Episode 3 was identified as Baseline ACT failure in the prior rollout map.
    if args.episode == 3:
        print("[NOTE] Episode 3 is identified as Baseline ACT failure; "
              "the requested filename contains 'act_orpa_failure'.")
    print("[SOURCE]", ", ".join(str(path) for path in files))
    print("[FONT]", font_file())
    print("[DURATION] {:.2f}s (shortest camera)".format(duration))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_name(args.out.stem + ".incomplete.mp4")
    inputs = []
    for path in files:
        inputs.extend(["-i", str(path)])
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + inputs + [
        "-filter_complex", create_filter(font_file(), args.fps, duration),
        "-map", "[outv]", "-an", "-shortest", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(tmp),
    ]
    try:
        run(command)
        final_duration = duration_seconds(tmp)
        if abs(final_duration - duration) > 0.25:
            raise RuntimeError("Unexpected output duration: {:.2f}s".format(final_duration))
        tmp.replace(args.out)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("[DONE] {} | 1280x960 | {:.2f}s | {} fps".format(args.out, final_duration, args.fps))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        sys.exit("[ERROR] " + str(exc))
