# Bielik + MEAI

**Bielik speaks Polish. MEAI speaks .NET.**

Copy-ready drafts for promoting both projects. These captions have not been posted to social media. The sample is an unofficial integration, not an endorsement by SpeakLeash or Microsoft.

## LinkedIn

[Download the ready-to-attach screenshot image](../media/linkedin/bielik-meai.png). It uses the original [iOS discovery screenshot](../media/android-meai/ios/screenshots/01-discover.png) and [Android chat screenshot](../media/android-meai/android/screenshots/07-real-chat.png), with unchanged app content, resized and framed for a 1200 x 1500 post image. The iOS image uses the user-supplied phone frame, which retains its original rights and is not covered by the app's MIT licence. The labels identify the platforms. Device provenance remains in the original [iOS capture report](../media/android-meai/ios/ui-report.json) and [Android capture report](../media/android-meai/android/ui-report.json).

Two copy-ready versions, Polish first and English second. Attach the same image to either post.

### Polski

```text
Bielik mówi po polsku. MEAI mówi językiem .NET.

Zbudowałem otwartoźródłową aplikację .NET 11 MAUI, która łączy je na iOS i Androidzie.

Bielik to polskojęzyczny model z otwartymi wagami. Microsoft.Extensions.AI (MEAI) daje nam IChatClient: wspólny interfejs .NET do obsługi rozmów z AI.

Mój adapter BielikChatClient łączy te dwa światy. Ten sam model widoku rozmowy obsługuje strumieniowe odpowiedzi i anulowanie generowania na obu platformach.

Bielik działa w Ollamie na Twoim Macu, nie na telefonie. Obie aplikacje używają MEAI do komunikacji z tym samym lokalnym modelem Bielik 11B v2.6 (Q4_K_M). Nie ma alternatywnego modelu ani awaryjnego przełączania do chmury.

Zrzuty ekranu pokazują rzeczywistą, natywną aplikację na iOS i Androidzie. Projekt korzysta z SDK .NET 11 w wersji preview.

Kod: https://github.com/kubaflo/bielik-maui
Bielik: https://bielik.ai/
MEAI: https://learn.microsoft.com/dotnet/ai/microsoft-extensions-ai

#Bielik #MEAI #dotnetMAUI #dotnet #OpenSource
```

### English

```text
Bielik speaks Polish. MEAI speaks .NET.

I built an open-source .NET 11 MAUI app that brings the two together on iOS and Android.

Bielik brings the Polish-language, open-weight model. Microsoft.Extensions.AI (MEAI) brings IChatClient: a common .NET interface for chat.

My BielikChatClient adapter connects them. The same chat view model handles streamed replies and cancellation on both platforms.

Bielik runs in Ollama on your Mac, not on the phone. Both apps use MEAI to talk to the same local Bielik 11B v2.6 (Q4_K_M) model. There is no alternate model or cloud fallback.

The screenshots show the actual native app on iOS and Android. The project uses the .NET 11 preview SDK.

Code: https://github.com/kubaflo/bielik-maui
Bielik: https://bielik.ai/
MEAI: https://learn.microsoft.com/dotnet/ai/microsoft-extensions-ai

#Bielik #MEAI #dotnetMAUI #dotnet #OpenSource
```

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
