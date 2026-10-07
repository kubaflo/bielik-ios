#!/usr/bin/env python3
"""Render deterministic portrait reels from verified, unaltered native captures."""

import argparse
import base64
import datetime
import hashlib
import io
import json
import math
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
MODEL = "hf.co/speakleash/Bielik-11B-v2.6-Instruct-GGUF:Q4_K_M"
FPS = 60
WIDTH = 1080
HEIGHT = 1920
THUMBNAIL = (90, 160)
REFERENCE = "https://lnkd.in/p/e4F-NJAc"


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def probe(path):
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ], capture_output=True, text=True).stdout)


def image_uri(data):
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def resource_name(path):
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else path.name


def snapshot(source, position):
    frame = run([
        "ffmpeg", "-hide_banner", "-v", "error", "-threads", "2",
        "-ss", f"{position:.6f}", "-i", str(source), "-frames:v", "1",
        "-vf", "scale='min(1080,iw)':-2", "-c:v", "mjpeg", "-q:v", "2",
        "-f", "image2pipe", "-",
    ], capture_output=True).stdout
    if not frame.startswith(b"\xff\xd8") or not frame.endswith(b"\xff\xd9"):
        raise RuntimeError(f"No complete native image was decoded at {position}s.")
    return frame


def read_capture(recording, report_path, platform):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report["platform"] != platform or report["model"] != MODEL or
            report.get("error") is not None or not report.get("actual_reply") or
            report["cloud_fallback"] or report["xctest_used"] or
            not report["native_clipboard_verified"]):
        raise ValueError(f"The {platform} capture does not satisfy the native-evidence policy.")
    if digest(recording) != report["native_recording_sha256"]:
        raise ValueError(f"The {platform} movie does not match its original capture report.")
    duration = float(probe(recording)["format"]["duration"])
    if abs(duration - report["native_duration_seconds"]) > 0.05:
        raise ValueError(f"The {platform} capture duration changed.")
    return report


def storyboard(report, edit):
    chapters = {item["name"]: item["start"] for item in report["chapters"]}
    generation = math.ceil((chapters["completed"] - chapters["streaming"] + 0.6) * 2) / 2
    if not 0.5 <= generation <= 15:
        raise ValueError("The recorded generation is outside the supported reel timing.")
    scenes = [
        ("hook", 2.5, "paper", None),
        ("discover", 3.5, "dark", chapters["discover"] + 0.35),
        ("ideas", 3.0, "paper", chapters["inspiration"] + 0.80),
        ("model", 2.5, "dark", chapters["model"] + (1.0 if report["platform"] == "ios" else 3.0)),
        ("connection", 3.0, "coral", chapters["connection"] + 0.65),
        ("compose", 2.5, "paper", chapters["streaming"] - 2.70),
        ("streaming", generation, "dark", chapters["streaming"]),
        ("answer", 3.0, "paper", chapters["completed"] + 0.45),
        ("copy", 2.0, "coral", chapters["copy"] - 0.15),
        ("outro", 3.5, "paper", None),
    ]
    if edit["native_recording_sha256"] != report["native_recording_sha256"]:
        raise ValueError("The edit map was calibrated for a different native recording.")
    overrides = edit["shots"]
    if set(overrides) - {scene[0] for scene in scenes}:
        raise ValueError("The edit map contains an unknown scene.")
    result = []
    start = 0
    for name, duration, theme, source_start in scenes:
        override = overrides.get(name, {})
        if set(override) - {"source_start", "duration"}:
            raise ValueError(f"The {name} edit contains an unsupported option.")
        duration = override.get("duration", duration)
        source_start = override.get("source_start", source_start)
        if (isinstance(duration, bool) or not isinstance(duration, (int, float)) or
                not math.isfinite(duration) or not 0 < duration <= 15 or
                duration * 2 != round(duration * 2)):
            raise ValueError(f"The {name} edit requires a positive, half-second-aligned duration.")
        if source_start is not None and (
                isinstance(source_start, bool) or not isinstance(source_start, (int, float)) or
                not math.isfinite(source_start)):
            raise ValueError(f"The {name} edit requires a finite native timestamp.")
        if source_start is not None and (
                source_start < 0 or source_start + duration > report["native_duration_seconds"]):
            raise ValueError(f"The {name} shot is outside the original recording.")
        result.append({
            "name": name, "start": start, "duration": duration, "theme": theme,
            "source_start": source_start, "playback_rate": 1 if source_start is not None else None,
        })
        start += duration
    return result, start


class NativeFrames:
    def __init__(self, source, scene, log):
        self.buffer = bytearray()
        self.expected = round(scene["duration"] * FPS)
        self.count = 0
        self.process = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-v", "error", "-threads", "2",
            "-ss", f'{scene["source_start"]:.6f}', "-i", str(source),
            "-vf", f"scale='min(1080,iw)':-2,fps={FPS}:start_time=0",
            "-frames:v", str(self.expected), "-c:v", "mjpeg", "-q:v", "2",
            "-threads", "2", "-f", "image2pipe", "-",
        ], stdout=subprocess.PIPE, stderr=log)

    def next(self):
        while True:
            end = self.buffer.find(b"\xff\xd9")
            if end >= 0:
                data = bytes(self.buffer[:end + 2])
                del self.buffer[:end + 2]
                if not data.startswith(b"\xff\xd8"):
                    raise RuntimeError("FFmpeg emitted an invalid native JPEG frame.")
                self.count += 1
                return data
            chunk = self.process.stdout.read1(65536)
            if not chunk:
                raise RuntimeError(f"Native footage ended at frame {self.count}/{self.expected}.")
            self.buffer.extend(chunk)

    def close(self, interrupted=False):
        if interrupted and self.process.poll() is None:
            self.process.terminate()
        self.process.stdout.close()
        code = self.process.wait(timeout=30)
        if not interrupted and (code or self.count != self.expected):
            raise RuntimeError(f"Native extraction failed: exit {code}, frames {self.count}/{self.expected}.")


def soundtrack(path, duration, scenes):
    rate = 48000
    samples = round(duration * rate)
    mix = np.zeros((samples, 2), dtype=np.float64)
    random = np.random.default_rng(20261007)
    beat = 0.5

    def add(position, sound, level, pan=0):
        start = round(position * rate)
        if start < 0:
            raise ValueError("A soundtrack event starts before the video.")
        end = min(samples, start + len(sound))
        if end <= start:
            return
        mix[start:end, 0] += sound[:end - start] * level * math.sqrt((1 - pan) / 2)
        mix[start:end, 1] += sound[:end - start] * level * math.sqrt((1 + pan) / 2)

    def tone(note, length, decay=2):
        t = np.arange(round(length * rate)) / rate
        frequency = 440 * 2 ** ((note - 69) / 12)
        voice = (np.sin(2 * np.pi * frequency * t) +
                 0.20 * np.sin(2 * np.pi * frequency * 2 * t) +
                 0.06 * np.sin(2 * np.pi * frequency * 3 * t))
        envelope = np.minimum(t / 0.015, 1) * np.exp(-decay * t)
        envelope *= np.minimum((length - t) / 0.08, 1)
        return voice * envelope

    for index in range(math.ceil(duration / beat)):
        position = index * beat
        if index % 2 == 0:
            t = np.arange(round(0.28 * rate)) / rate
            phase = 2 * np.pi * (48 * t + 95 * 0.03 * (1 - np.exp(-t / 0.03)))
            add(position, np.sin(phase) * np.exp(-t * 18) * np.minimum(t / 0.003, 1), 0.38)
        if index % 4 == 2:
            t = np.arange(round(0.11 * rate)) / rate
            noise = random.normal(0, 1, len(t))
            high = np.concatenate(([0.0], np.diff(noise)))
            add(position, high * np.exp(-t * 48) * np.minimum(t / 0.003, 1), 0.045, 0.10)
        t = np.arange(round(0.045 * rate)) / rate
        noise = random.normal(0, 1, len(t))
        hat = np.concatenate(([0.0], np.diff(noise))) * np.exp(-t * 110)
        add(position + beat / 2, hat, 0.015, -0.28 if index % 2 else 0.28)
        roots = [45, 41, 48, 43]
        root = roots[(index // 8) % len(roots)]
        if index % 2 == 0:
            add(position, tone(root - 12, 0.70, 4), 0.23)
        melody = [69, 72, 76, 79, 76, 72, 67, 71]
        add(position + 0.02, tone(melody[index % 8], 0.70, 5), 0.08,
            0.25 * math.sin(index * 1.1))

    for chord_index, position in enumerate(np.arange(0, duration, beat * 8)):
        notes = [(57, 60, 64, 67), (53, 57, 60, 64), (60, 64, 67, 71), (55, 59, 62, 69)]
        for note_index, note in enumerate(notes[chord_index % 4]):
            add(float(position) + note_index * 0.025, tone(note, 3.8, 0.65),
                0.028, (note_index - 1.5) / 3)

    for scene in scenes[1:]:
        length = 0.24
        t = np.arange(round(length * rate)) / rate
        noise = random.normal(0, 1, len(t))
        swoosh = np.convolve(noise, np.ones(12) / 12, mode="same") * np.sin(np.pi * t / length) ** 2
        add(max(0, scene["start"] - 0.08), swoosh, 0.045, -0.1)
    fade = min(round(rate * 0.45), samples // 2)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix = np.tanh(mix * 1.35)
    peak = np.max(np.abs(mix))
    if peak <= 0:
        raise RuntimeError("The original procedural soundtrack is silent.")
    pcm = np.round(mix / peak * 0.80 * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


class QuietHandler(SimpleHTTPRequestHandler):
    allowed = frozenset({
        "/scripts/reels/composition.html",
        "/Bielik/Resources/Fonts/Geologica-SemiBold.ttf",
        "/Bielik/Resources/Fonts/SourceSansPro-Regular.otf",
        "/Bielik/Resources/Fonts/SourceSansPro-Semibold.otf",
        "/Bielik/Resources/Images/official_bielik_logo.png",
        "/Bielik/Resources/Images/official_bielik_background.png",
        "/Bielik/Resources/Images/official_bielik_mascot.png",
        "/Bielik/Resources/Images/official_bielik_network.png",
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format_string, *args):
        pass

    def do_GET(self):
        if urlsplit(self.path).path not in self.allowed:
            self.send_error(404, "Not a composition resource")
            return
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in self.allowed:
            self.send_error(404, "Not a composition resource")
            return
        super().do_HEAD()


def thumbnail(jpeg):
    with Image.open(io.BytesIO(jpeg)) as frame:
        if frame.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"The composition emitted the wrong resolution: {frame.size}")
        return np.asarray(frame.convert("RGB").resize(THUMBNAIL, Image.Resampling.BOX)).copy()


def verify_frames(video, expected, log):
    process = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-v", "error", "-xerror", "-threads", "2",
        "-i", str(video), "-map", "0:v:0", "-vf",
        f"scale={THUMBNAIL[0]}:{THUMBNAIL[1]}:flags=area",
        "-pix_fmt", "rgb24", "-fps_mode", "passthrough", "-f", "rawvideo", "-",
    ], stdout=subprocess.PIPE, stderr=log)
    frame_bytes = THUMBNAIL[0] * THUMBNAIL[1] * 3
    worst_mean = 0
    worst_tile = 0
    count = 0
    try:
        for reference in expected:
            data = process.stdout.read(frame_bytes)
            if len(data) != frame_bytes:
                raise RuntimeError(f"Delivery decode ended unexpectedly at frame {count}.")
            actual = np.frombuffer(data, dtype=np.uint8).reshape(THUMBNAIL[1], THUMBNAIL[0], 3)
            difference = np.abs(actual.astype(np.int16) - reference.astype(np.int16))
            mean = float(np.mean(difference))
            tile = float(np.max(difference.reshape(16, 10, 9, 10, 3).mean(axis=(1, 3, 4))))
            worst_mean = max(worst_mean, mean)
            worst_tile = max(worst_tile, tile)
            if mean > 5.5 or tile > 22:
                raise RuntimeError(f"Frame {count} differs from its render: mean {mean:.3f}, tile {tile:.3f}.")
            count += 1
        if process.stdout.read(1):
            raise RuntimeError("The delivery contains unexpected extra frames.")
        if process.wait(timeout=30):
            raise RuntimeError("The delivery failed its full-frame decode.")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=30)
    return {"frames_compared": count, "worst_mean_error": worst_mean, "worst_tile_error": worst_tile}


def contact_sheet(frames, destination):
    sheet = Image.new("RGB", (1124, math.ceil(len(frames) / 4) * 510), "#091633")
    font = ImageFont.truetype(str(ROOT / "Bielik/Resources/Fonts/SourceSansPro-Regular.otf"), 20)
    for index, (label, jpeg) in enumerate(frames):
        with Image.open(io.BytesIO(jpeg)) as image:
            image = image.convert("RGB").resize((270, 480), Image.Resampling.LANCZOS)
        x = 10 + (index % 4) * 280
        y = 10 + (index // 4) * 510
        sheet.paste(image, (x, y))
        ImageDraw.Draw(sheet).text((x, y + 482), label, font=font, fill="white")
    sheet.save(destination, quality=92)


def render_platform(page, platform, recordings, reports, edits, args, work):
    report = reports[platform]
    scenes, duration = storyboard(report, edits[platform])
    source = recordings[platform]
    stem = f"{platform}-demo"
    destination = args.output / f"{stem}.mp4"
    if destination.exists() and not args.replace and not args.preview:
        raise FileExistsError(f"Use --replace to update an existing demo: {destination}")
    hero = {name: snapshot(path, reports[name]["chapters"][0]["start"] + 0.55)
            for name, path in recordings.items()}
    settings = {
        "platform": platform, "fps": FPS, "duration": duration, "scenes": scenes,
        "stills": {
            "hero": image_uri(hero[platform]),
            "iosHero": image_uri(hero["ios"]),
            "androidHero": image_uri(hero["android"]),
        },
    }
    ready = page.evaluate("settings => window.bielikReel.prepare(settings)", settings)
    if ready != {"width": WIDTH, "height": HEIGHT, "fontsReady": True}:
        raise RuntimeError(f"The composition is not ready: {ready}")
    previews = []
    fingerprints = []
    poster = None

    def frame(time, data=None, previous=None):
        result = page.evaluate(
            "async args => await window.bielikReel.render(args.time, args.frame, args.previous)",
            {"time": time, "frame": image_uri(data) if data else None,
             "previous": image_uri(previous) if previous else None},
        )
        if result["nativeDraws"] < 1:
            raise RuntimeError("The frame contains no real native UI.")
        return base64.b64decode(result["jpeg"], validate=True)

    if args.preview:
        for scene in scenes:
            for offset in (min(0.65, scene["duration"] / 3), min(1.65, scene["duration"] - 0.1)):
                data = snapshot(source, scene["source_start"] + offset) if scene["source_start"] is not None else None
                jpeg = frame(scene["start"] + offset, data)
                previews.append((f'{scene["name"]} / {scene["start"] + offset:.2f}s', jpeg))
        contact_sheet(previews, args.work_dir / f"{platform}-preview.jpg")
        return

    audio = work / f"{platform}-soundtrack.wav"
    visual = work / f"{platform}-visual.mp4"
    final = work / f"{stem}.mp4"
    soundtrack(audio, duration, scenes)
    with (args.work_dir / f"{platform}-render.log").open("w") as log:
        encoder = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-v", "error", "-f", "image2pipe",
            "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
            "-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p",
            "-c:v", "libx264", "-threads", "2", "-preset", "medium", "-crf", "18",
            "-profile:v", "high", "-level:v", "4.2", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
            "-movflags", "+faststart", "-an", str(visual),
        ], stdin=subprocess.PIPE, stderr=log)
        native = None
        previous = None
        complete = False
        try:
            for scene in scenes:
                if scene["source_start"] is not None:
                    native = NativeFrames(source, scene, log)
                count = round(scene["duration"] * FPS)
                print(f'{platform}: {scene["name"]}, {count} frames', flush=True)
                for index in range(count):
                    data = native.next() if native else None
                    time = scene["start"] + index / FPS
                    jpeg = frame(time, data, previous if index < round(0.35 * FPS) else None)
                    encoder.stdin.write(jpeg)
                    fingerprints.append(thumbnail(jpeg))
                    if index == min(round(0.9 * FPS), count - 1):
                        previews.append((f'{scene["name"]} / {time:.2f}s', jpeg))
                    if scene["name"] == "hook" and index == round(1.8 * FPS):
                        poster = jpeg
                    if index == count - 1:
                        previous = data
                if native:
                    native.close()
                    native = None
            encoder.stdin.close()
            if encoder.wait(timeout=120):
                raise RuntimeError("The visual encoder failed; see the render log.")
            complete = True
        finally:
            if native:
                native.close(interrupted=True)
            if encoder.poll() is None:
                encoder.terminate()
                encoder.wait(timeout=30)
        if not complete or poster is None:
            raise RuntimeError("The reel rendering is incomplete.")
        run([
            "ffmpeg", "-hide_banner", "-v", "error", "-i", str(visual), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", "loudnorm=I=-16:TP=-2:LRA=7", "-ar", "48000", "-t", str(duration),
            "-movflags", "+faststart", str(final),
        ], stderr=log)
        comparison = verify_frames(final, fingerprints, log)
    metadata = probe(final)
    video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
    expected_frames = round(duration * FPS)
    if (video["codec_name"] != "h264" or video["pix_fmt"] != "yuv420p" or
            (video["width"], video["height"]) != (WIDTH, HEIGHT) or
            video["avg_frame_rate"] != f"{FPS}/1" or int(video["nb_frames"]) != expected_frames or
            abs(float(metadata["format"]["duration"]) - duration) > 0.04 or
            audio_stream["codec_name"] != "aac"):
        raise RuntimeError("The delivered reel does not satisfy the media contract.")
    with final.open("rb") as movie:
        header = movie.read(1024 * 1024)
    if not 0 <= header.find(b"moov") < header.find(b"mdat"):
        raise RuntimeError("The delivery is not a fast-start MP4.")
    published = dict(report)
    published.update({
        "rendered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "published_recording": destination.name,
        "published_recording_sha256": digest(final),
        "published_duration_seconds": duration,
        "published_bytes": final.stat().st_size,
        "resolution": [WIDTH, HEIGHT],
        "frames_per_second": FPS,
        "presentation": "Ten beat-paced HTML/canvas scenes, native UI close-ups, eased camera motion and editorial wipes.",
        "source_recording_reused": True,
        "raw_recording": resource_name(source),
        "native_footage_speed": 1,
        "native_footage_edited": True,
        "source_to_output_timeline": scenes,
        "edit_map": resource_name(args.edit_map),
        "edit_map_sha256": digest(args.edit_map),
        "timing_basis": edits["timing_basis"],
        "original_capture_report_sha256": digest(args.ios_report if platform == "ios" else args.android_report),
        "native_stills": {
            name: {
                "raw_recording": resource_name(recordings[name]),
                "native_recording_sha256": reports[name]["native_recording_sha256"],
                "source_time_seconds": round(reports[name]["chapters"][0]["start"] + 0.55, 6),
            }
            for name in recordings
        },
        "audio": "Original procedural stereo instrumental and transition sounds; 120 BPM, AAC, -16 LUFS target.",
        "audio_source": "scripts/render-reels.py soundtrack(); no borrowed recording, speech or third-party music.",
        "composition": "scripts/reels/composition.html",
        "composition_sha256": digest(ROOT / "scripts/reels/composition.html"),
        "renderer": "Playwright WebKit; decoded native image frames, no browser video layer or desktop automation.",
        "renderer_sha256": digest(Path(__file__)),
        "style_reference": REFERENCE,
        "full_decode_verified": True,
        "all_frames_compared_to_render": comparison,
        "poster": f"{stem}.jpg",
    })
    args.output.mkdir(parents=True, exist_ok=True)
    report_output = work / f"{stem}.json"
    report_output.write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    poster_output = work / f"{stem}.jpg"
    poster_output.write_bytes(poster)
    contact_sheet(previews, args.work_dir / f"{platform}-final-contact-sheet.jpg")
    for path in (final, report_output, poster_output):
        path.replace(args.output / path.name)
    print(f"{platform}: verified {expected_frames} frames, {duration:.1f}s, {published['published_bytes']} bytes", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ios-recording", type=Path, required=True)
    parser.add_argument("--ios-report", type=Path, required=True)
    parser.add_argument("--android-recording", type=Path, required=True)
    parser.add_argument("--android-report", type=Path, required=True)
    parser.add_argument("--platform", choices=("ios", "android", "both"), default="both")
    parser.add_argument("--output", type=Path, default=ROOT / "media/demos")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--edit-map", type=Path, default=ROOT / "scripts/reels/edit-map.json")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"Required tool is missing: {tool}")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    recordings = {"ios": args.ios_recording.resolve(), "android": args.android_recording.resolve()}
    reports = {
        "ios": read_capture(recordings["ios"], args.ios_report, "ios"),
        "android": read_capture(recordings["android"], args.android_report, "android"),
    }
    edits = json.loads(args.edit_map.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{server.server_port}/scripts/reels/composition.html"
    try:
        with urllib.request.urlopen(address, timeout=5) as response:
            if response.status != 200 or b'canvas id="reel"' not in response.read():
                raise RuntimeError("The loopback composition server is not responsive.")
        with tempfile.TemporaryDirectory(prefix="bielik-reel-", dir=args.work_dir) as temporary:
            with sync_playwright() as playwright:
                browser = playwright.webkit.launch(headless=True)
                try:
                    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
                    failures = []
                    page.on("pageerror", lambda error: failures.append(str(error)))
                    page.on("requestfailed", lambda request: failures.append(f"{request.url}: {request.failure}"))
                    page.route("**/*", lambda route: route.continue_() if (
                        route.request.url.startswith(f"http://127.0.0.1:{server.server_port}/")
                    ) else route.abort())
                    page.goto(address, wait_until="networkidle")
                    for platform in (("ios", "android") if args.platform == "both" else (args.platform,)):
                        render_platform(page, platform, recordings, reports, edits, args, Path(temporary))
                    if failures:
                        raise RuntimeError(f"Composition browser errors: {failures}")
                finally:
                    browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
