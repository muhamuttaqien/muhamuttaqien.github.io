#!/usr/bin/env python3
"""Generate ORPA website videos directly from episode_N_video_*.mp4.

Python 3.8+, FFmpeg with libx264 + drawtext. No HDF5 access, no source writes.
Run --init-map, edit rollout_map.json, then run production.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

TASKS = {
    'snack_box_transfer': ('Snack Box Transfer', 3, True),
    'chip_tube_opening': ('Chip Tube Opening', 3, True),
    'object_sorting': ('Object Sorting', 1, False),
}
CAMERAS = ('high', 'low', 'left_wrist', 'right_wrist')

# Match ORPA hero: Helvetica, slate #2d3748, white labels,
# green/red status communicated solely by small colored squares.
SLATE = '0x2d3748'
SUCCESS = '0x22c55e'
FAILURE = '0xef6464'



def cmd(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    if proc.returncode:
        raise RuntimeError('Command failed: {}\n{}'.format(' '.join(map(str, args)), proc.stderr[-3500:]))
    return proc.stdout


def check_tools():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Install ffmpeg / ffprobe first (sudo apt install ffmpeg)')
    output = cmd(['ffmpeg', '-hide_banner', '-encoders'])
    if 'libx264' not in output:
        raise RuntimeError('Your FFmpeg lacks libx264')
    # Use the same requested Helvetica face as the ORPA hero transitions.
    # Linux commonly resolves Helvetica to Nimbus Sans, a close substitute.
    if shutil.which('fc-match'):
        font = cmd(['fc-match', '-f', '%{file}', 'Helvetica']).strip()
        if font and Path(font).is_file():
            print('[FONT] Helvetica (fontconfig): {}'.format(font))
            return font
    for font in ('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(font).is_file():
            print('[FONT] Helvetica substitute: {}'.format(font))
            return font
    raise RuntimeError('No Helvetica-compatible font found. Install fontconfig and a sans-serif font.')


def clip_info(path):
    d = json.loads(cmd(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height,avg_frame_rate:format=duration',
                        '-of', 'json', str(path)]))
    if not d.get('streams'):
        raise ValueError('No video stream: {}'.format(path))
    stream = d['streams'][0]
    if int(stream.get('width', 0)) < 10 or int(stream.get('height', 0)) < 10:
        raise ValueError('Invalid video resolution: {}'.format(path))
    if float(d['format']['duration']) < .2:
        raise ValueError('Video is too short: {}'.format(path))
    return d


def ffescape(s):
    return str(s).replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")


def bottom_caption(font, title, method, status='neutral', width=1280, height=720):
    """Hero-style single-line bar: centered status square and white method only."""
    bar_h = round(height * 116 / 1080)
    left = round(width * 70 / 1920)
    marker = max(8, round(height * 18 / 1080))
    text_size = max(18, round(height * 42 / 1080))
    middle = height - bar_h / 2
    status = status.lower()
    accent = {'success': SUCCESS, 'failure': FAILURE, 'neutral': '0xffffff'}[status]
    label = ffescape(method)  # No task name in the on-video label
    # ffmpeg's drawtext and drawbox intentionally match the hero's lower-third.
    filters = [
        'drawbox=x=0:y={}:w={}:h={}:color=black@0.68:t=fill'.format(
            height-bar_h, width, bar_h),
        'drawbox=x={}:y={}:w={}:h={}:color={}:t=fill'.format(
            left, int(round(middle-marker/2)), marker, marker, accent),
        "drawtext=fontfile='{}':text='{}':fontsize={}:fontcolor=white:x={}:y={}-text_h/2".format(
            ffescape(font), label, text_size, left+marker+round(height*19/1080), middle)
    ]
    return ','.join(filters)


def panel_caption(font, label):
    """Four-camera tags: Helvetica, white text, semi-transparent slate overlay."""
    return (
        'drawbox=x=0:y=ih-46:w=iw:h=46:color={slate}@0.85:t=fill,'
        "drawtext=fontfile='{font}':text='{label}':fontsize=23:"
        'fontcolor=white:x=18:y=h-46+(46-text_h)/2'
    ).format(slate=SLATE, font=ffescape(font), label=ffescape(label))


def encode(args, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.incomplete.mp4')
    if temp.exists():
        temp.unlink()
    try:
        cmd(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + args +
            ['-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
             '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temp)])
        clip_info(temp)
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


CAMERA_SUFFIXES = {
    'high': 'high_camera',
    'low': 'low_camera',
    'left_wrist': 'left_wrist_camera',
    'right_wrist': 'right_wrist_camera',
}


def source(root, task, episode, cam='high'):
    """Read the original recorder filenames without renaming them."""
    return root / ('orpa_' + task) / ('episode_{}_video_{}.mp4'.format(
        episode, CAMERA_SUFFIXES[cam]))


def discover(root):
    """Find available episode indices from original MP4 names; do not infer labels."""
    import re
    found = {}
    pattern = re.compile(r'^episode_(\d+)_video_(?:high|low|left_wrist|right_wrist)_camera\.mp4$')
    for task in TASKS:
        folder = root / ('orpa_' + task)
        indexes = set()
        if folder.is_dir():
            for file in folder.iterdir():
                match = pattern.fullmatch(file.name)
                if match:
                    indexes.add(int(match.group(1)))
        found[task] = sorted(indexes)
    return found


def init_map(root, destination):
    found = discover(root)
    print('[SCAN] Input videos in {}'.format(root))
    for task, indexes in found.items():
        print('  orpa_{}: {}'.format(task, indexes if indexes else 'NO EPISODES FOUND'))
    if destination.exists():
        raise FileExistsError('Mapping exists; not overwriting: {}'.format(destination))
    mapping = {}
    for task, (_label, failures, has_success) in TASKS.items():
        mapping[task] = {
            'available_episodes': found[task],
            'act_orpa_success': None,
            'act_failures': [None] * failures,
        }
    destination.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
    print('[SAVED]', destination)
    print('[ACTION] Set act_orpa_success and act_failures using actual episode indexes.')


def load_map(path):
    if not path.is_file():
        raise FileNotFoundError('Rollout map missing: {}. Run --init-map first.'.format(path))
    mapping = json.loads(path.read_text(encoding='utf-8'))
    for task, (_label, failures, has_success) in TASKS.items():
        conf = mapping.get(task)
        if not isinstance(conf, dict):
            raise ValueError('Missing task in map: {}'.format(task))
        success = conf.get('act_orpa_success')
        items = conf.get('act_failures')
        if not isinstance(items, list) or len(items) != failures:
            raise ValueError('{} must have exactly {} entries in act_failures'.format(task, failures))
        if not has_success and success is not None:
            raise ValueError('{} has no ACT + ORPA success video'.format(task))
        indexes = ([success] if has_success else []) + items
        for index in indexes:
            if index is not None and (type(index) is not int or index < 0):
                raise ValueError('{}: episode IDs must be nonnegative integers or null'.format(task))
        chosen = [index for index in indexes if index is not None]
        if len(chosen) != len(set(chosen)):
            raise ValueError('{}: same episode assigned to multiple outcomes'.format(task))
    return mapping


def individual(src, dst, title, method, result, font, fps, failure_number=None):
    success = result.upper() == 'SUCCESS'
    sub = 'ACT + ORPA' if success else 'Baseline ACT'
    filt = ('[0:v]fps={f},split=2[bg][fg];'
            '[bg]scale=1280:720:force_original_aspect_ratio=increase,'
            'crop=1280:720,boxblur=20:5,eq=brightness=-0.12[back];'
            '[fg]scale=960:720:force_original_aspect_ratio=decrease,setsar=1[front];'
            '[back][front]overlay=(W-w)/2:(H-h)/2,'
            '{caption}[v]').format(
                f=fps,
                caption=bottom_caption(font, title, sub,
                                       'success' if success else 'failure'))
    encode(['-i', str(src), '-filter_complex', filt, '-map', '[v]'], dst)


def multicamera(files, dst, task_label, font, fps):
    labels = ('High Camera', 'Low Camera', 'Left Wrist', 'Right Wrist')
    filters = []
    for i, lab in enumerate(labels):
        filters.append('[{i}:v]fps={fps},scale=640:480,setsar=1,{caption}[v{i}]'.format(
            i=i, fps=fps, caption=panel_caption(font, lab)))
    duration = min(float(clip_info(f)['format']['duration']) for f in files)
    # Four camera panels only: no top heading strip.
    filters.append('color=c={}:s=1280x960:r={}:d={:.4f}[bg]'.format(
        SLATE, fps, duration))
    filters.append('[bg][v0]overlay=0:0:shortest=1[t0]')
    filters.append('[t0][v1]overlay=640:0:shortest=1[t1]')
    filters.append('[t1][v2]overlay=0:480:shortest=1[t2]')
    filters.append('[t2][v3]overlay=640:480:shortest=1[v]')
    args = []
    for file in files:
        args.extend(['-i', str(file)])
    encode(args + ['-filter_complex', ';'.join(filters), '-map', '[v]', '-shortest'], dst)


def comparison(failure, success, dst, task_label, font, fps):
    """Independent ACT / ORPA rollouts with hero-consistent labels."""
    f = ffescape(font)
    filt = (
        '[0:v]fps={fps},scale=640:480,setsar=1[l];'
        '[1:v]fps={fps},scale=640:480,setsar=1[r];'
        '[l][r]hstack=inputs=2:shortest=1[duo];'
        # Bottom status bar only; no top heading or added top padding.
        '[duo]pad=1280:540:0:0:color={slate},'
        'drawbox=x=0:y=480:w=1280:h=60:color=black@0.68:t=fill,'
        'drawbox=x=17:y=502:w=15:h=15:color={fail}:t=fill,'
        'drawbox=x=657:y=502:w=15:h=15:color={success}:t=fill,'
        "drawtext=fontfile='{font}':text='Baseline ACT':"
        'fontsize=25:fontcolor=white:x=44:y=480+(60-text_h)/2,'
        "drawtext=fontfile='{font}':text='ACT + ORPA':"
        'fontsize=25:fontcolor=white:x=684:y=480+(60-text_h)/2,'
        'null[v]'
    ).format(fps=fps, slate=SLATE, fail=FAILURE, success=SUCCESS, font=f)
    encode(['-i', str(failure), '-i', str(success),
            '-filter_complex', filt, '-map', '[v]', '-shortest'], dst)


def highlight(a, b, dst, font, fps):
    # Short clips from both real ACT + ORPA successes; no baseline footage.
    f = ('[0:v]trim=start=0:duration=4,setpts=PTS-STARTPTS,fps={fps},'
         'scale=960:720:force_original_aspect_ratio=decrease,'
         'pad=1280:720:(ow-iw)/2:(oh-ih)/2:color={slate},'
         '{t1}[a];'
         '[1:v]trim=start=0:duration=4,setpts=PTS-STARTPTS,fps={fps},'
         'scale=960:720:force_original_aspect_ratio=decrease,'
         'pad=1280:720:(ow-iw)/2:(oh-ih)/2:color={slate},'
         '{t2}[b];[a][b]concat=n=2:v=1:a=0[v]').format(
            fps=fps, slate=SLATE,
            t1=bottom_caption(font, 'Snack Box Transfer', 'ACT + ORPA', 'success'),
            t2=bottom_caption(font, 'Chip Tube Opening', 'ACT + ORPA', 'success'))
    encode(['-i', str(a), '-i', str(b), '-filter_complex', f, '-map', '[v]'], dst)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('inputs'),
                   help='Root containing orpa_chip_tube_opening, etc.')
    p.add_argument('--map', type=Path, default=Path('rollout_map.json'))
    p.add_argument('--init-map', action='store_true',
                   help='Scan episode_N_video_*.mp4 and generate unlabeled template')
    p.add_argument('--scan', action='store_true', help='Show available episode indexes')
    p.add_argument('--out', type=Path, default=Path('output'))
    p.add_argument('--fps', type=int, default=30, choices=(24, 25, 30, 50))
    p.add_argument('--allow-partial', action='store_true',
                   help='Render only currently mapped and available videos')
    args = p.parse_args()

    if args.scan:
        for task, ids in discover(args.input).items():
            print('orpa_{}: {}'.format(task, ids if ids else 'NO EPISODES FOUND'))
        return 0
    if args.init_map:
        init_map(args.input, args.map)
        return 0

    mapping = load_map(args.map)
    font = check_tools()
    jobs = []
    assigned = []
    for task, (label, failures, has_success) in TASKS.items():
        conf = mapping[task]
        success = conf['act_orpa_success']
        if has_success and success is not None:
            jobs.append(('individual', task, 'act_orpa_success',
                         [source(args.input, task, success)]))
            assigned.append((task, 'act_orpa_success', success))
        for index, episode in enumerate(conf['act_failures'], start=1):
            if episode is None:
                continue
            variant = 'act_failure_{}'.format(index)
            jobs.append(('individual', task, variant,
                         [source(args.input, task, episode)]))
            assigned.append((task, variant, episode))
        if has_success and success is not None:
            if conf['act_failures'][0] is not None:
                jobs.append(('comparison', task, 'baseline_vs_orpa',
                             [source(args.input, task, conf['act_failures'][0]),
                              source(args.input, task, success)]))
            jobs.append(('multicamera', task, 'act_orpa_success',
                         [source(args.input, task, success, cam)
                          for cam in CAMERAS]))
    snack_success = mapping['snack_box_transfer']['act_orpa_success']
    chip_success = mapping['chip_tube_opening']['act_orpa_success']
    if snack_success is not None and chip_success is not None:
        jobs.append(('highlight', 'orpa', 'two_task_highlight',
                     [source(args.input, 'snack_box_transfer', snack_success),
                      source(args.input, 'chip_tube_opening', chip_success)]))

    unassigned_outputs = 14 - len(jobs)
    missing = [(k, t, v, [str(f) for f in files if not f.is_file()])
               for k, t, v, files in jobs if not all(f.is_file() for f in files)]
    if (unassigned_outputs or missing) and not args.allow_partial:
        print('[STOP] {} unassigned outputs; {} mapped outputs missing files.'.format(
              unassigned_outputs, len(missing)))
        for task in TASKS:
            conf = mapping[task]
            print('  {}: success={} failures={}'.format(task, conf['act_orpa_success'], conf['act_failures']))
        for kind, task, variant, absent in missing:
            print('  {} / {} / {}: {}'.format(kind, task, variant, ', '.join(absent)))
        print('Edit --map or use --allow-partial.')
        return 2

    hashes = {}
    for task, variant, episode in assigned:
        file = source(args.input, task, episode)
        if file.is_file():
            digest = sha256(file)
            if digest in hashes:
                raise ValueError('Identical MP4 assigned to different rollouts:\n{}\n{}'.format(
                                 hashes[digest], file))
            hashes[digest] = str(file)

    report = []
    for kind, task, variant, files in jobs:
        name = '{}_{}_{}.mp4'.format(task, variant, kind)
        target = args.out / name
        if not all(f.is_file() for f in files):
            report.append({'output': name, 'status': 'missing_source',
                           'missing': [str(f) for f in files if not f.is_file()]})
            print('[SKIP]', name)
            continue
        try:
            for file in files:
                clip_info(file)
            title = TASKS[task][0] if task in TASKS else 'ORPA'
            if kind == 'individual':
                success = variant == 'act_orpa_success'
                individual(files[0], target, title,
                           'ACT + ORPA' if success else 'Baseline ACT',
                           'SUCCESS' if success else 'FAILURE', font, args.fps,
                           failure_number=(int(variant.rsplit('_', 1)[-1])
                                           if not success else None))
            elif kind == 'comparison':
                comparison(*files, target, title, font, args.fps)
            elif kind == 'multicamera':
                multicamera(files, target, title, font, args.fps)
            elif kind == 'highlight':
                highlight(*files, target, font, args.fps)
            report.append({'output': name, 'status': 'created',
                           'sources': [str(f) for f in files]})
            print('[SAVED]', target)
        except Exception as e:
            report.append({'output': name, 'status': 'error', 'reason': str(e)})
            print('[ERROR]', name, str(e), file=sys.stderr)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'build_report.json').write_text(json.dumps({
        'assigned_rollouts': assigned,
        'unassigned_outputs': unassigned_outputs,
        'videos': report,
    }, indent=2), encoding='utf-8')
    total = sum(x['status'] == 'created' for x in report)
    print('[RESULT] {} / 14 videos created'.format(total))
    print('[REPORT]', args.out / 'build_report.json')
    return 0 if total == 14 else 1


if __name__ == '__main__':
    sys.exit(main())
