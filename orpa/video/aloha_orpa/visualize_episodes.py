#!/usr/bin/env python3
"""Visualize recorded ALOHA/GR00T demonstrations (read-only HDF5).

Supports recordings created by record_episodes_gr00t.py, including
episodes without effort, audio, or RealSense data.
Requires: numpy, h5py, cv2, matplotlib. No ROS, SciPy or pyrealsense2.
"""
import argparse
import math
import os
import shutil
import subprocess

import cv2
import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_FPS = 50.0  # ALOHA's nominal DT=0.02
JOINTS = ("waist", "shoulder", "elbow", "forearm_roll",
          "wrist_angle", "wrist_rotate", "gripper")
CAMERA_ORDER = ("cam_high", "cam_low", "cam_left_wrist", "cam_right_wrist")


def optional_array(root, path):
    return root[path][()] if path in root else None


def available_cameras(root):
    group = root.get("/observations/images")
    if not isinstance(group, h5py.Group):
        return []
    names = [name for name, ds in group.items()
             if isinstance(ds, h5py.Dataset) and ds.ndim == 4
             and ds.shape[0] > 0 and ds.shape[-1] == 3]
    return sorted(names, key=lambda n: (CAMERA_ORDER.index(n) if n in CAMERA_ORDER
                                        else len(CAMERA_ORDER), n))


def save_video(root, path, fps):
    """Export one combined camera video and one separate video per camera."""
    names = available_cameras(root)
    if not names:
        print("[SKIP] No RGB camera arrays found")
        return
    datasets = [root["/observations/images/" + name] for name in names]
    frames = min(ds.shape[0] for ds in datasets)
    if any(len(ds) != frames for ds in datasets):
        print("[WARN] Camera streams have different lengths; using shortest")
    columns = min(2, len(names))
    rows = math.ceil(len(names) / columns)
    tw, th = 640, 480

    def open_writer(filename, size):
        writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"mp4v"),
                                 fps, size)
        if not writer.isOpened():
            raise RuntimeError("Could not open video writer: " + filename)
        return writer

    # Filenames: episode_0_video.mp4, episode_0_video_high_camera.mp4, etc.
    suffixes = {
        "cam_high": "high_camera",
        "cam_low": "low_camera",
        "cam_left_wrist": "left_wrist_camera",
        "cam_right_wrist": "right_wrist_camera",
    }
    stem = path[:-4] if path.endswith(".mp4") else path
    if stem.endswith("_video"):
        stem = stem[:-6]
    writers = []
    outputs = []
    try:
        combined = open_writer(path, (columns * tw, rows * th))
        writers.append(combined)
        for name in names:
            suffix = suffixes.get(name, name)
            filename = stem + "_video_" + suffix + ".mp4"
            individual = open_writer(filename, (tw, th))
            writers.append(individual)
            outputs.append(filename)

        for i in range(frames):
            canvas = np.zeros((rows * th, columns * tw, 3), dtype=np.uint8)
            for j, (name, ds) in enumerate(zip(names, datasets)):
                frame = ds[i]
                if frame.dtype != np.uint8:
                    frame = np.clip(frame, 0, 255).astype(np.uint8)
                if frame.shape[0] <= 0 or frame.shape[1] <= 0:
                    raise ValueError("Invalid camera frame shape: " + name)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
                writers[j + 1].write(frame)
                row, col = divmod(j, columns)
                x, y = col * tw, row * th
                canvas[y:y + th, x:x + tw] = frame
                cv2.rectangle(canvas, (x, y), (x + 265, y + 32), (0, 0, 0), -1)
                cv2.putText(canvas, name, (x + 8, y + 23),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            combined.write(canvas)
    finally:
        for writer in writers:
            writer.release()
    for filename in [path] + outputs:
        print("[SAVED] {} ({} frames)".format(filename, frames))


def plot_series(values, path, title, fps, comparison=None):
    values = np.asarray(values)
    if values.ndim != 2 or values.shape[0] == 0:
        print("[SKIP] {}: expected a nonempty 2D dataset".format(title))
        return
    steps, dims = values.shape
    names = ([side + "_" + joint for side in ("left", "right") for joint in JOINTS]
             if dims == 14 else ["joint_{}".format(i) for i in range(dims)])
    t = np.arange(steps) / fps
    fig, axs = plt.subplots(dims, 1, figsize=(12, max(4, dims * 1.8)),
                            sharex=True, squeeze=False)
    for idx, ax in enumerate(axs[:, 0]):
        ax.plot(t, values[:, idx], linewidth=1, label="Observed" if comparison is not None else title)
        if comparison is not None and comparison.ndim == 2 and idx < comparison.shape[1]:
            count = min(steps, comparison.shape[0])
            ax.plot(t[:count], comparison[:count, idx], linewidth=1,
                    alpha=0.8, label="Command")
        ax.set_ylabel(names[idx], fontsize=8)
        ax.grid(alpha=0.25)
        if idx == 0:
            ax.legend(loc="upper right", fontsize=8)
    axs[-1, 0].set_xlabel("Time (s), nominal rate")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print("[SAVED] " + path)



def parse_resolution(value):
    try:
        width, height = (int(x) for x in value.lower().split("x"))
        if width < 320 or height < 240 or width % 2 or height % 2:
            raise ValueError
        return width, height
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError("Resolution must be even WIDTHxHEIGHT, at least 320x240")


def fit_frame(rgb, width, height):
    """Fit an RGB HDF5 image into a BGR canvas without cropping or stretching."""
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    if h == 0 or w == 0:
        raise ValueError("Empty camera image")
    scale = min(width / w, height / h)
    target = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    scaled = cv2.resize(bgr, target, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    canvas = np.full((height, width, 3), (24, 26, 30), dtype=np.uint8)
    x, y = (width - target[0]) // 2, (height - target[1]) // 2
    canvas[y:y+target[1], x:x+target[0]] = scaled
    return canvas


def put_label(canvas, label, at, scale=0.65):
    x, y = at
    cv2.putText(canvas, label, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(canvas, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (245, 245, 245), 1, cv2.LINE_AA)


def read_camera(root, name, frame):
    return root["/observations/images/" + name][frame]


def camera_layout(root, names, index, size, mode, primary):
    width, height = size
    if mode == "showcase":
        return fit_frame(read_camera(root, primary, index), width, height)
    main = primary if primary in names else names[0]
    others = [n for n in names if n != main]
    if not others:
        return fit_frame(read_camera(root, main, index), width, height)
    sidebar = max(160, width // 3)
    gap = max(4, width // 320)
    left_width = width - sidebar - gap
    canvas = np.full((height, width, 3), (24, 26, 30), dtype=np.uint8)
    canvas[:, :left_width] = fit_frame(read_camera(root, main, index), left_width, height)
    put_label(canvas, main, (16, 29))
    for j, name in enumerate(others):
        y0 = j * height // len(others)
        y1 = (j + 1) * height // len(others)
        x0 = left_width + gap
        tile = fit_frame(read_camera(root, name, index), sidebar, y1 - y0)
        canvas[y0:y1, x0:x0 + sidebar] = tile
        put_label(canvas, name, (x0 + 10, y0 + 27), scale=0.48)
    return canvas


def technical_layout(root, names, index, size, primary, qpos, actions, fps, total):
    width, height = size
    left = width * 58 // 100
    canvas = np.full((height, width, 3), (24, 26, 30), dtype=np.uint8)
    canvas[:, :left] = fit_frame(read_camera(root, primary, index), left, height)
    put_label(canvas, primary, (16, 29))
    if qpos is None and actions is None:
        put_label(canvas, "No joint data available", (left + 14, height // 2), 0.52)
        return canvas
    x0, x1 = left + 32, width - 18
    y0, y1 = 75, height - 75
    cv2.rectangle(canvas, (x0, y0), (x1, y1), (65, 69, 76), 1)
    series = []
    for label, data, color in (("Observed joint 0", qpos, (235, 195, 95)),
                                ("Commanded joint 0", actions, (110, 200, 245))):
        if data is not None and data.ndim == 2 and len(data) > 0 and data.shape[1] > 0:
            series.append((label, np.asarray(data[:min(len(data), total), 0], dtype=float), color))
    if not series:
        put_label(canvas, "No 2D joint data available", (x0, height // 2), 0.46)
        return canvas
    finite = np.concatenate([s[np.isfinite(s)] for _, s, _ in series])
    if len(finite) == 0:
        put_label(canvas, "No finite joint data", (x0, height // 2), 0.48)
        return canvas
    lo, hi = float(finite.min()), float(finite.max())
    if hi - lo < 1e-8:
        lo, hi = lo - 1, hi + 1
    put_label(canvas, "Joint 0: recorded qpos / action", (x0, 38), 0.47)
    for j, (label, values, color) in enumerate(series):
        if len(values) > 1:
            points = []
            for k, v in enumerate(values):
                if np.isfinite(v):
                    xx = x0 + round(k / max(1, total - 1) * (x1 - x0))
                    yy = y1 - round((float(v) - lo) / (hi - lo) * (y1 - y0))
                    points.append((xx, yy))
            for a, b in zip(points, points[1:]):
                cv2.line(canvas, a, b, color, 2, cv2.LINE_AA)
        cv2.putText(canvas, label, (x0, height - 40 + j * 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    cursor = x0 + round(min(index, total - 1) / max(1, total - 1) * (x1 - x0))
    cv2.line(canvas, (cursor, y0), (cursor, y1), (220, 220, 220), 1)
    return canvas


def open_showcase_writer(path, fps, size, codec):
    """Prefer browser-friendly H.264 via installed ffmpeg; fallback to OpenCV mp4v."""
    width, height = size
    if codec == "h264" and shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
               "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
               "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", path]
        return subprocess.Popen(cmd, stdin=subprocess.PIPE), "ffmpeg"
    if codec == "h264":
        print("[WARN] ffmpeg not found; falling back to mp4v codec")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise RuntimeError("Cannot open video writer: " + path)
    return writer, "opencv"


def export_research_video(root, stem, args):
    names = available_cameras(root)
    if not names:
        print("[SKIP] No RGB camera arrays found")
        return
    primary = args.camera if args.camera in names else ("cam_high" if "cam_high" in names else names[0])
    if args.camera and args.camera not in names:
        raise ValueError("Camera {!r} not found; available: {}".format(args.camera, names))
    total = min(root["/observations/images/" + name].shape[0] for name in names)
    start = min(total, math.floor(args.start * args.fps))
    end = total if args.end is None else min(total, math.ceil(args.end * args.fps))
    if end <= start:
        raise ValueError("Empty clip: check --start, --end and --fps")
    frames = range(start, end)
    output = args.output or stem + "_" + args.mode + ".mp4"
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    qpos = optional_array(root, "/observations/qpos") if args.mode == "technical" else None
    actions = optional_array(root, "/action") if args.mode == "technical" else None
    writer, backend = open_showcase_writer(output, args.fps * args.speed, args.resolution, args.codec)
    preview = None
    count = 0
    try:
        for index in frames:
            if args.mode == "technical":
                canvas = technical_layout(root, names, index, args.resolution, primary,
                                          qpos, actions, args.fps, total)
            else:
                canvas = camera_layout(root, names, index, args.resolution, args.mode, primary)
            if args.title:
                cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 48), (20, 23, 29), -1)
                put_label(canvas, args.title, (16, 31), 0.65)
            cv2.rectangle(canvas, (0, canvas.shape[0] - 10), (canvas.shape[1], canvas.shape[0]),
                          (38, 42, 46), -1)
            progress = (index - start + 1) / (end - start)
            cv2.rectangle(canvas, (0, canvas.shape[0] - 10),
                          (round(canvas.shape[1] * progress), canvas.shape[0]), (225, 170, 90), -1)
            if preview is None:
                preview = canvas.copy()
            if backend == "ffmpeg":
                writer.stdin.write(canvas.tobytes())
            else:
                writer.write(canvas)
            count += 1
    finally:
        if backend == "ffmpeg":
            writer.stdin.close()
            code = writer.wait()
            if code:
                raise RuntimeError("ffmpeg encoding failed (code {})".format(code))
        else:
            writer.release()
    if args.preview and preview is not None:
        preview_path = os.path.splitext(output)[0] + "_preview.webp"
        if not cv2.imwrite(preview_path, preview, [cv2.IMWRITE_WEBP_QUALITY, 85]):
            raise RuntimeError("Could not write preview: " + preview_path)
        print("[SAVED] " + preview_path)
    print("[SAVED] {} ({} frames, {:.2f} fps, {})".format(output, count, args.fps * args.speed, backend))


def main():
    parser = argparse.ArgumentParser(description="Visualize an ALOHA/GR00T HDF5 episode")
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--episode_idx", required=True, type=int)
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS)
    parser.add_argument("--no_video", action="store_true")
    parser.add_argument("--mode", choices=("legacy", "showcase", "multicam", "technical"),
                        default="legacy", help="Default legacy retains all existing outputs")
    parser.add_argument("--camera", help="Main camera; defaults to cam_high if available")
    parser.add_argument("--resolution", type=parse_resolution, default=(1280, 720),
                        help="Even WIDTHxHEIGHT for new modes (default: 1280x720)")
    parser.add_argument("--start", type=float, default=0.0, help="Clip start in original episode seconds")
    parser.add_argument("--end", type=float, help="Clip end in original episode seconds")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed for new modes")
    parser.add_argument("--title", default="", help="Optional title overlaid on output")
    parser.add_argument("--output", help="Output MP4 path for new modes")
    parser.add_argument("--codec", choices=("h264", "mp4v"), default="h264")
    parser.add_argument("--preview", action="store_true", help="Also export a WebP preview")
    args = parser.parse_args()
    if args.start < 0 or not math.isfinite(args.start) or (args.end is not None and
            (not math.isfinite(args.end) or args.end <= args.start)):
        parser.error("--start must be >= 0 and --end must be greater than --start")
    if args.speed <= 0 or not math.isfinite(args.speed):
        parser.error("--speed must be a finite positive number")
    if args.mode != "legacy" and args.no_video:
        parser.error("--no_video is only supported in legacy mode")
    if args.fps <= 0 or not math.isfinite(args.fps):
        parser.error("--fps must be a finite positive number")

    stem = os.path.join(args.dataset_dir, "episode_{}".format(args.episode_idx))
    filename = stem + ".hdf5"
    if not os.path.isfile(filename):
        parser.error("Episode not found: " + filename)

    with h5py.File(filename, "r") as root:
        print("[INFO] Reading " + filename)
        print("[INFO] Cameras: " + str(available_cameras(root)))
        qpos = optional_array(root, "/observations/qpos")
        actions = optional_array(root, "/action")
        effort = optional_array(root, "/observations/effort")
        if args.mode != "legacy":
            export_research_video(root, stem, args)
            print("[DONE] HDF5 source unchanged")
            return
        if not args.no_video:
            save_video(root, stem + "_video.mp4", args.fps)
        if qpos is not None:
            plot_series(qpos, stem + "_qpos.png", "Joint positions vs actions",
                        args.fps, comparison=actions)
        else:
            print("[SKIP] No /observations/qpos")
        if effort is not None:
            plot_series(effort, stem + "_effort.png", "Joint effort", args.fps)
        else:
            print("[SKIP] No /observations/effort")
        if (qpos is not None and actions is not None
                and qpos.ndim == 2 and actions.shape == qpos.shape):
            plot_series(actions - qpos, stem + "_error.png",
                        "Command minus observed position", args.fps)
        else:
            print("[SKIP] Tracking-error plot requires matching qpos and action")
    print("[DONE] HDF5 source unchanged")


if __name__ == "__main__":
    main()
