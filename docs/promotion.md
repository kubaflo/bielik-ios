# Bielik + MEAI

**Bielik speaks Polish. MEAI speaks .NET.**

Copy-ready drafts for promoting both projects. These captions have not been posted to social media. The sample is an unofficial integration, not an endorsement by SpeakLeash or Microsoft.

## LinkedIn

Polish AI, a common .NET API, and two native mobile apps.

Bielik brings the Polish-language, open-weight model. Microsoft.Extensions.AI (MEAI) brings `IChatClient`: a shared .NET interface with typed streaming responses and cancellation.

In this open-source .NET 11 MAUI sample, `BielikChatClient` connects the two. The same chat view model runs on iOS and Android. The reels show real source code and an actual streamed Polish answer, not a mocked conversation.

The phone is the native client. Bielik 11B v2.6 runs locally through Ollama on a Mac, not on the phone. No alternate model or cloud fallback.

Build with both:

- Bielik: https://bielik.ai/
- MEAI: https://learn.microsoft.com/dotnet/ai/microsoft-extensions-ai
- Sample and videos: https://github.com/kubaflo/bielik-maui

Recorded on an iOS simulator and Android emulator; edited footage is not a speed benchmark.

#Bielik #MEAI #dotnet #dotnetMAUI #OpenSource

## Instagram Reels / short caption

Bielik speaks Polish. MEAI speaks .NET.

Polish open-weight AI + Microsoft.Extensions.AI + native iOS and Android with .NET 11 MAUI. Real C#, real streaming, a real Bielik reply.

Bielik runs on the Mac; the phones are native clients. No cloud fallback.

Build it: github.com/kubaflo/bielik-maui

Discover Bielik: bielik.ai

Discover MEAI: learn.microsoft.com/dotnet/ai/microsoft-extensions-ai

#Bielik #MEAI #dotnet #dotnetMAUI #OpenSource

## Gemini handoff: exactly 30 seconds

[Download the raw screenshots and prompts](../media/gemini-reel/bielik-meai-gemini-kit.zip), unzip it, and upload the four screenshots for your chosen platform to Gemini. Paste the [iOS prompt](../media/gemini-reel/prompt-ios.txt) or [Android prompt](../media/gemini-reel/prompt-android.txt). The [preview](../media/gemini-reel/preview.jpg) is only an index; upload the full-resolution originals.

All eight images are **unchanged raw app screenshots**: discovery, model, MEAI details and real chat on both platforms. There are no poster frames, overlays, crops or re-encoding. The source-hash [manifest](../media/gemini-reel/manifest.json) identifies the original captures. Both English prompts give MEAI and Bielik equal prominence, preserve native Polish UI, and distinguish Mac inference from the mobile clients.

Each requested new edit is **30 seconds**, not the existing 35-second videos below. If the selected Gemini video tool only supports short clips, each prompt supplies a four-clip plan: 8 + 8 + 8 + 6 seconds. Capabilities and attachment limits depend on the tool and account. Check the final duration and preserve native screenshots as intact image layers rather than accepting generated lettering or invented chat.

No assets were uploaded to Gemini. Recreate this local handoff with `python3 scripts/export-promo-kit.py`; it reuses published evidence without running a simulator or model.

## Ready-to-upload files

| Platform footage | Reel | Cover |
| --- | --- | --- |
| iOS simulator | [ios-demo.mp4](../media/demos/ios-demo.mp4) | [ios-demo.jpg](../media/demos/ios-demo.jpg) |
| Android emulator | [android-demo.mp4](../media/demos/android-demo.mp4) | [android-demo.jpg](../media/demos/android-demo.jpg) |

Both edits are 35 seconds, 1080 x 1920, 60 fps, with an original soundtrack. Raw recordings, editing provenance and reproduction commands are in the [developer guide](development.md#reels-style-demos).
