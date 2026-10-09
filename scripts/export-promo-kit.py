#!/usr/bin/env python3
"""Export genuine screenshot references and a 30-second Gemini reel brief."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "media/gemini-reel"
PROMPT = OUTPUT / "prompt.txt"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def describe(path):
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {"bytes": path.stat().st_size, "sha256": digest(path), "dimensions": list(image.size)}


def main():
    if not PROMPT.is_file() or "exactly 30.0 seconds" not in PROMPT.read_text():
        raise ValueError("The 30-second user handoff prompt is missing.")
    screenshots = OUTPUT / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    captures = [
        ("01-ios-discover", "ios", "native_discover", "HOME"),
        ("02-android-discover", "android", "native_discover", "HOME"),
        ("03-ios-model", "ios", "pinned_model_screen", "MODEL"),
        ("04-android-model", "android", "pinned_model_screen", "MODEL"),
        ("05-ios-meai", "ios", "meai_and_essentials_policy", "MEAI"),
        ("06-android-meai", "android", "meai_and_essentials_policy", "MEAI"),
        ("07-ios-real-chat", "ios", "real_polish_streamed_reply", "CHAT"),
        ("08-android-real-chat", "android", "real_polish_streamed_reply", "CHAT"),
    ]
    entries = []
    substitutions = {"ios": {"PLATFORM": "iOS"}, "android": {"PLATFORM": "Android"}}
    for name, platform, step_name, token in captures:
        evidence_path = ROOT / f"media/android-meai/{platform}/ui-report.json"
        evidence = json.loads(evidence_path.read_text())
        step = next(item for item in evidence["steps"] if item["name"] == step_name)
        if evidence["error"] is not None or step["status"] != "passed" or evidence["xctest_used"]:
            raise ValueError(f"The {platform} screenshot lacks successful native capture evidence.")
        source = evidence_path.parent / step["screenshot"]
        destination = screenshots / f"{name}.png"
        shutil.copyfile(source, destination)
        if digest(destination) != digest(source):
            raise ValueError(f"The {platform} native screenshot changed during export.")
        substitutions[platform][token] = destination.name
        entries.append({
            "file": str(destination.relative_to(OUTPUT)),
            "kind": "Unchanged native simulator/emulator screenshot; no overlays or edits.",
            "platform": platform,
            "source": str(source.relative_to(ROOT)),
            "capture_report": str(evidence_path.relative_to(ROOT)),
            "captured_at": evidence["recorded_at"],
            **describe(destination),
        })
    prompts = []
    for platform, tokens in substitutions.items():
        text = PROMPT.read_text()
        for token, value in tokens.items():
            text = text.replace("{{" + token + "}}", value)
        if "{{" in text:
            raise ValueError(f"The {platform} prompt has unresolved template fields.")
        path = OUTPUT / f"prompt-{platform}.txt"
        path.write_text(text, encoding="utf-8")
        prompts.append(path)

    sheet = Image.new("RGB", (1144, 1060), "#091633")
    font = ImageFont.truetype(str(ROOT / "Bielik/Resources/Fonts/SourceSansPro-Regular.otf"), 21)
    for index, entry in enumerate(entries):
        with Image.open(OUTPUT / entry["file"]) as image:
            image = image.convert("RGB")
            image.thumbnail((270, 480), Image.Resampling.LANCZOS)
            x = 10 + index % 4 * 286
            y = 10 + index // 4 * 530
            sheet.paste(image, (x + (270 - image.width) // 2, y))
        label = Path(entry["file"]).stem.replace("-", " ")
        ImageDraw.Draw(sheet).text((x, y + 487), label, font=font, fill="#FAF8F3")
    preview = OUTPUT / "preview.jpg"
    sheet.save(preview, quality=94)

    manifest = {
        "purpose": "Raw app screenshots and separate 30-second iOS/Android Gemini reel prompts.",
        "target_duration_seconds": 30,
        "target_aspect_ratio": "9:16",
        "target_resolution": [1080, 1920],
        "inference_runtime": "Pinned Bielik 11B v2.6 Q4_K_M in Ollama on the Mac, not the phone.",
        "meai": "Microsoft.Extensions.AI / IChatClient, not another model.",
        "screenshots": entries,
        "prompts": [{"file": path.name, "sha256": digest(path)} for path in prompts],
        "rights": "Original artwork rights and trademarks are retained; not relicensed under the app MIT license.",
        "asset_manifest_source": "Bielik/Resources/Raw/website_assets.json",
        "notices_source": "Bielik/Resources/Raw/third_party_notices.txt",
        "uploaded_to_gemini": False,
        "new_capture_or_inference_run": False,
    }
    manifest_path = OUTPUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    archive_path = OUTPUT / "bielik-meai-gemini-kit.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*prompts, manifest_path, preview, *[OUTPUT / item["file"] for item in entries]]:
            archive.write(path, str(path.relative_to(OUTPUT)))
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != 12:
            raise ValueError("The exported Gemini handoff archive is incomplete.")
    print(f"Exported {len(entries)} unchanged raw screenshots and two prompts: {archive_path}")
    print(f"Archive size: {archive_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
