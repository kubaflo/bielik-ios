# Developer guide

[Back to the README](../README.md)

Build, run and verify **Bielik MAUI** on iOS and Android. This standalone application consumes .NET MAUI NuGet packages; it does not build the MAUI framework source. Run all commands below from the repository root, not from `docs/`.

The pinned model is `hf.co/speakleash/Bielik-11B-v2.6-Instruct-GGUF:Q4_K_M`. Ollama runs it on the Mac; both phones are native MEAI clients, not on-device inference engines. No other model or cloud fallback is configured.

## Contents

- [Requirements](#requirements)
- [MEAI and MAUI Essentials AI](#meai-and-maui-essentials-ai)
- [Run the exact local model](#run-the-exact-local-model)
- [Build and install on iOS](#build-and-install-on-ios)
- [Build and install on Android](#build-and-install-on-android)
- [Checks, screenshots and recordings](#reproduce-the-checks-and-captures)
- [Release and physical phones](#release-and-physical-phones)
- [Privacy](#privacy-and-implementation-boundaries) and [licenses](#license)

## Website identity, native interface

The design follows the website's actual styles and assets rather than the earlier burgundy/serif interpretation. A white wordmark header leads into the official gradient and line-drawn eagle; coral primary buttons and outlined secondary actions carry through to the chat, model and settings pages. Navy chat bubbles, native controls and a pinned composer retain the app's original local-only behavior. The home screen's **Ustaw lokalny serwer** action opens connection settings.

Colors and font families come from the site's published styles: coral `#E76450`, navy `#091633`, slate `#3B4556`, Geologica and Source Sans Pro. Small accent text uses a darker coral for readability. Website imagery, the app icon, splash and all four font faces are packaged with MAUI; there are no remote image requests or embedded website/WebView.

The original website background remains unchanged. A tiny, locally generated transparent-white PNG reproduces the hero overlay's alpha fade from `209/255` to `128/255` on both platforms. This avoids the Android preview's opaque rendering of alpha gradient brushes without modifying or duplicating the official artwork.

The [asset manifest](../Bielik/Resources/Raw/website_assets.json) records exact website image URLs, original SHA-256 hashes, pinned font revisions and the project's explicit authorization to use the website images. The [packaged notices](../Bielik/Resources/Raw/third_party_notices.txt) retain source attribution and separate artwork/font rights.

Historical [initial screenshots](../media/screenshots), [original local-inference walkthrough](../media/local-bielik-walkthrough.mp4), [initial progress recording](../media/progress/ui-progress.mp4), [first creator-branding update](../media/progress/official-branding.mp4) and [earlier website-style evidence](../media/website-style) remain unchanged as progress evidence, not previews of the current implementation.

## Requirements

| Component | Version used |
| --- | --- |
| .NET SDK | `11.0.100-preview.6.26359.118` |
| Workload set | `11.0.100-preview.6.26364.2` |
| MAUI Controls | `11.0.0-preview.6.26360.8` |
| Essentials AI | `11.0.0-preview.6.26360.8` |
| MEAI abstractions | `10.3.0` |
| Xcode | 26.6 |
| Simulators | iPhone 17 Pro and iPhone SE (3rd generation), iOS 26.5 |
| Android SDK / verified emulator | API 37 / Pixel 9, API 35, ARM64 |
| Android emulator | `36.6.11.0` |
| Java used | JDK 21.0.8 |
| Ollama | 0.32.14 |
| DevFlow agent and project-local CLI | `0.1.0-preview.12.26421.1` |

Install the SDK specified in [`global.json`](../global.json), Xcode and its iOS simulator runtime, and the Android SDK with an ARM64 emulator image. Android requires API 24 or newer; iOS requires 17 or newer. The SDK and MAUI APIs are previews. Ollama needs enough memory for an 11B model; the selected quantization downloads approximately 6.7 GB of weights. Python 3 is needed for the verification scripts, and FFmpeg is needed only for media compression.

```bash
git clone https://github.com/kubaflo/bielik-maui.git
cd bielik-maui
dotnet --version
dotnet workload restore Bielik/Bielik.csproj
dotnet tool restore

# Only if these tools are missing:
brew install ollama ffmpeg
```

The local tool manifest deliberately pins the CLI to the agent version. An older global `maui` CLI can inspect the app but cannot honor the newer agent's mutation-lease protocol; use `dotnet maui` here.

[`NuGet.config`](../NuGet.config) uses Microsoft's single public `dotnet-public` feed for the pinned preview packages, avoiding dependence on machine-specific feeds or multiple-source central-package-management warnings.

## MEAI and MAUI Essentials AI

[`BielikChatClient`](../Bielik.Core/BielikChatClient.cs) implements `Microsoft.Extensions.AI.IChatClient` over the existing validated Ollama transport. The shared chat view model actually consumes this interface on both platforms. Streaming produces standard `ChatResponseUpdate` objects, completion reasons and `UsageContent`; non-streaming calls aggregate a `ChatResponse`. Native UI metrics remain available as `bielik.generation_metrics`.

The adapter resolves the saved private endpoint for each request and preserves the exact model, CPU inference, bounded whole-turn context, cancellation and explicit errors. It rejects alternate models, images, tool calls, system overrides and unsupported options before sending them. Only successfully completed exchanges enter conversation memory.

**`Microsoft.Maui.Essentials.AI` does not provide Android native inference yet.** Following [Microsoft's AI documentation](https://learn.microsoft.com/dotnet/maui/ai/?view=net-maui-10.0), the app includes the matching Essentials AI package and exposes its actual platform/provider policy on the Model screen:

| Capability | iOS | Android |
| --- | --- | --- |
| Pinned Bielik through MEAI | Local Mac inference, iOS 17+ client | Local Mac inference, Android API 24+ client |
| `AppleIntelligenceChatClient` | Apple Intelligence API, iOS 26+, **not selected** | No implementation |
| `NLEmbeddingGenerator` | Apple NaturalLanguage embeddings, iOS 13+, **not registered** | No implementation |

On iOS 26+, the diagnostics instantiate `AppleIntelligenceChatClient` only to read its MEAI provider/model metadata. They never send it a prompt or claim its model is ready. Actual Apple inference additionally requires eligible hardware, enabled Apple Intelligence and downloaded weights; a simulator/OS check alone is insufficient. On older iOS and on Android, the screen explicitly describes the limitation.

Apple's system model and `NLEmbeddingGenerator`'s embedding model are not Bielik, so neither replaces the pinned weights. There is no unsupported Android on-device AI claim, hidden Apple/Gemini switch, embedding feature or cloud fallback. Experimental diagnostics are suppressed only where the specific API is used; other warnings remain errors.

## Run the exact local model

Start a dedicated, loopback-only Ollama server in one terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

In another terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 \
  ollama pull hf.co/speakleash/Bielik-11B-v2.6-Instruct-GGUF:Q4_K_M

curl --fail http://127.0.0.1:11434/api/version
```

Do not start a second server if the intended local instance already owns that port. The app checks `/api/tags` for the exact model before sending a conversation. Missing weights produce an explicit installation error, not a fallback response.

If the model download repeatedly fails with HTTP/2 stream cancellations, restart **only the server you started** with `GODEBUG=http2client=0` added to its environment, then repeat the pull. Ollama resumes partially downloaded weights.

**Runtime choice:** this app explicitly requests CPU inference (`num_gpu=0`). On this M4 Max with Ollama 0.32.14, a clean Metal runner repeatedly produced control characters and an incomplete response, while the same weights and prompt completed correctly on CPU. The [untouched comparison](../media/runtime-comparison.json) preserves both outcomes. This is an observed runtime-specific limitation, not a claim that Bielik generally cannot use GPUs. No model substitution is involved.

## Build and install on iOS

List available devices and choose a dedicated simulator:

```bash
xcrun simctl list devices available
export BIELIK_SIMULATOR="<your-simulator-UDID>"
xcrun simctl boot "$BIELIK_SIMULATOR"
xcrun simctl bootstatus "$BIELIK_SIMULATOR" -b
```

Skip `boot` if that simulator is already booted. None of these commands opens or takes control of the desktop Simulator window.

```bash
dotnet restore Bielik/Bielik.csproj -p:Configuration=Debug

dotnet build Bielik/Bielik.csproj \
  --no-restore --framework net11.0-ios --configuration Debug \
  -p:RuntimeIdentifier=iossimulator-arm64 \
  -p:EnableCodeSigning=true -p:CodesignKey=-

xcrun simctl install "$BIELIK_SIMULATOR" \
  Bielik/bin/Debug/net11.0-ios/iossimulator-arm64/Bielik.app
xcrun simctl launch --terminate-running-process \
  "$BIELIK_SIMULATOR" dev.bielik.companion
```

Simulator ad-hoc signing is intentional. Disabling signing can cause iOS to kill the app before managed startup. Allow the first launch to finish loading; a splash-screen screenshot is not evidence that the pages rendered.

The default Debug endpoint is `http://127.0.0.1:11434`, which reaches this Mac from its iOS simulator. Open **Ustawienia** and check the connection, then use **Rozmowa**. Inspiration cards populate the composer without automatically sending a prompt.

For a separate recording simulator while another preview already uses DevFlow port 9235, choose a free automation port at launch:

```bash
SIMCTL_CHILD_BIELIK_DEVFLOW_PORT=9237 \
  xcrun simctl launch --terminate-running-process \
  "$BIELIK_SIMULATOR" dev.bielik.companion
```

This Debug-only override leaves the normal port at 9235. Values outside `1-65535` or non-integer values fail startup explicitly; Release still has no automation agent. Use the chosen port with the capture script's `--agent-port` option, and do not target a simulator someone is using.

If NuGet is unreachable but the exact dependencies are already cached, append `--source "$HOME/.nuget/packages"` to `dotnet restore`. This workaround was used on the development machine; it is not a replacement for fetching dependencies on a clean machine.

Restore the complete multi-target project without a global `TargetFramework`/`TargetFrameworks` override. Such an override also retargets the generic `Bielik.Core` project during restore. Select the desired framework and runtime in the subsequent **`--no-restore` build**, as shown here.

## Build and install on Android

Create a dedicated AVD from an installed ARM64 system image, or select one you already use for this app:

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
avdmanager create avd --name Bielik_Pixel_9_API_35 \
  --package 'system-images;android-35;google_apis_playstore;arm64-v8a' \
  --device pixel_9

# Keep this running in its own terminal. No desktop emulator window is opened.
emulator -avd Bielik_Pixel_9_API_35 -no-window -no-audio \
  -no-boot-anim -no-snapshot -gpu swiftshader -port 5580
```

Do not overwrite an existing AVD or reuse occupied emulator ports. The recorded run used a new isolated Pixel 9 image at 1080 x 2424, not the user's existing emulator.

```bash
export BIELIK_ANDROID=emulator-5580
adb -s "$BIELIK_ANDROID" wait-for-device
adb -s "$BIELIK_ANDROID" shell getprop sys.boot_completed # wait until this is 1

dotnet restore Bielik/Bielik.csproj -p:Configuration=Debug
dotnet build Bielik/Bielik.csproj --no-restore \
  --framework net11.0-android --configuration Debug \
  -p:RuntimeIdentifier=android-arm64

adb -s "$BIELIK_ANDROID" install --no-incremental -r \
  Bielik/bin/Debug/net11.0-android/android-arm64/dev.bielik.companion-Signed.apk
activity=$(adb -s "$BIELIK_ANDROID" shell cmd package resolve-activity \
  --brief dev.bielik.companion | tr -d '\r' | tail -1)
adb -s "$BIELIK_ANDROID" shell am start -W -n "$activity"
adb -s "$BIELIK_ANDROID" forward --no-rebind tcp:9236 tcp:9235
curl --fail http://127.0.0.1:9236/api/v1/agent/status
```

The Android Debug APK embeds its managed assemblies/runtime so direct `adb install` works without an IDE's fast-deployment directory. Its default endpoint, `http://10.0.2.2:11434`, reaches the Mac's loopback Ollama server through the emulator gateway. `127.0.0.1` inside Android would refer to the emulator, not the Mac. Port **9236** is the forwarded Android automation port; the iOS preview can continue using **9235**.

The same locally packaged artwork and font faces are used on Android. Settings use Android's `monospace` font rather than iOS-only Menlo. Release disables cleartext traffic and Android backups are disabled in both configurations. This setup does not expose Ollama beyond the host.

## Reproduce the checks and captures

The ordinary service tests require no simulator or model:

```bash
dotnet test Bielik.Core.Tests/Bielik.Core.Tests.csproj
```

They cover local-only endpoints, the Android gateway, the Release HTTPS policy, exact-model enforcement, NDJSON streaming, malformed and truncated responses, cancellation, and whole-turn history bounds. MEAI cases additionally verify response aggregation, token usage, metadata, endpoint changes, unsupported-input rejection and disposal of an in-flight response. The verified service suite has **69 passing cases**.

Run actual inference probes against the installed model:

```bash
python3 scripts/test-model.py \
  --output media/model-evaluation.json \
  --code-output /tmp/bielik-generated-code/Generated.cs
```

The script records untouched responses, weight metadata, timings and generation rates for arithmetic, strict JSON, schema-constrained JSON, conversation memory, Polish explanation, and C# generation. It does not execute the generated code. Inspect that output before compiling it. These are small functional samples, not a general model-quality benchmark.

### Actual Bielik results

The [raw CPU evaluation](../media/model-evaluation.json), [original native UI evidence](../media/ui-report.json) and [fresh website-style native UI evidence](../media/website-style/ui-report.json) were recorded on this Mac. The website-style run repeated actual streaming, memory, cancellation and error recovery using the same pinned model; it did not rerun the separate seven-probe model evaluation. The model digest is `7eb4bbe15c57c14e87ce5fa1132a01371ed1cc0b1626811c44667756e19359cc`.

| Probe | Observed result |
| --- | --- |
| `17 + 25`, numeric answer only | Passed: `42` |
| JSON instructed only by prompt | **Failed strict format**: correct object enclosed in Markdown fences |
| Same JSON with an Ollama schema | Passed: valid, exact JSON object |
| Remember and recall `bursztyn` | Passed through both the direct API and native app |
| Two-sentence Polish explanation | Coherent Polish and correct basic distinction; speed/privacy claims remain deployment-dependent |
| Generated C# | Correct implementation, but **failed the no-Markdown instruction** |
| Compiled C# body | [7/7 checks passed](../media/generated-code-checks.txt), including negative values, empty input, `long` overflow safety and null rejection; only enclosing fences were removed |

Substantive direct CPU responses ran at approximately **19-25 tokens/second**. The original native explanation measured **21.1 tokens/second**; the earlier website-style recording measured **19.3 tokens/second**. The current MEAI samples measured **21.7 tokens/second on Android** and **23.2 tokens/second on iOS**. These are individual Mac CPU runs, not phone-performance benchmarks. Tiny replies have noisier rates. The model-probe command intentionally exits **1** for the observed strict-JSON failure; that is a model-quality finding, not a failing application test. Do not treat instruction-only output as guaranteed machine-readable JSON or executable source. The model's claims about faster execution, improved privacy or reduced energy use are not guarantees; they depend on the deployment.

With the Debug app installed and the local model ready:

```bash
python3 scripts/capture-ios.py \
  --simulator "$BIELIK_SIMULATOR" \
  --output /tmp/bielik-capture
```

The capture script resets this app's conversation and endpoint. The historical website-style iOS recording passed **15 native checks**, including navigation, presets, public-endpoint rejection, a real streamed response, native clipboard copying, preserving conversation when rechecking an unchanged endpoint, conversation recall, generation cancellation, and recovery from an unavailable-server error without fallback. The current MEAI run adds explicit provider-policy verification on both platforms. Captures use a **non-forced, exclusive DevFlow lease** and release it afterward. They never use XCTest, desktop input, or another app's window.

The separate [branding report](../media/website-style/branding-report.json) checks official artwork placement, accessible image descriptions, 44-point minimum touch targets and home-to-settings navigation using native `windowBounds`, not unscrolled layout coordinates. The [compact-phone report](../media/website-style/compact-report.json) and [compact screenshots](../media/website-style/compact-screenshots) verify the 375 × 667-point iPhone SE layout, reachable scrollable controls and pinned composer. The compact chat screenshot is intentionally scrolled to show all presets. These additional layout captures make no inference claim.

The shared native runner now supports both platforms:

```bash
python3 scripts/capture-android.py \
  --device "$BIELIK_ANDROID" --agent-port 9236 \
  --output /tmp/bielik-android-capture
python3 scripts/capture-ios.py \
  --simulator "$BIELIK_SIMULATOR" --agent-port 9235 \
  --output /tmp/bielik-maui-ios-capture
```

The new run includes the MEAI/Essentials policy screen. Discovery/model scroll positions are reset before their overview captures, and the official network illustration is checked against actual window bounds, so repeated tours do not mistake a retained scrolled panel for the model overview. Android clipboard verification pastes the actual system clipboard into the native editor; it does not assume copying succeeded. Recording uses the device's `screenrecord` process, stops only its known PID, pulls the completed MP4 and removes only that owned temporary file. iOS continues using `simctl`, never XCTest. The scripts acquire non-forced DevFlow leases and release them on exit.

All **16 current native checks passed on each platform**: [Android report](../media/android-meai/android/ui-report.json) and [iOS report](../media/android-meai/ios/ui-report.json). The separate [Android progress report](../media/android-meai/android/progress-report.json) and [iOS progress report](../media/android-meai/ios/progress-report.json) each contain nine UI-only checks and make no generation claim. [Compact Android evidence](../media/android-meai/android/compact-report.json) verifies reachable hero actions, a pinned 48-point composer/send control, and scrollable Essentials diagnostics at 360 x 640 points; its [screenshots](../media/android-meai/android/compact-screenshots) likewise make no inference claim.

Add `--tour-only` for a UI progress recording before weights are installed; that mode explicitly makes no inference claim. Use a dedicated simulator for either mode.

Compress a capture without changing its content:

```bash
ffmpeg -i /tmp/bielik-capture/local-bielik-walkthrough.mp4 \
  -vf 'scale=720:-2,fps=24' -c:v libx264 -crf 23 \
  -movflags +faststart -an /tmp/bielik-capture/local-bielik-walkthrough-small.mp4
ffprobe -v error -show_entries format=duration,size \
  /tmp/bielik-capture/local-bielik-walkthrough-small.mp4
```

The original [UI progress movie](../media/progress/ui-progress.mp4) documents the native app before inference was available. The [Android](../media/android-meai/android/ui-progress.mp4) and [iOS](../media/android-meai/ios/ui-progress.mp4) verification tours show the website-style interface separately from the actual-inference walkthroughs. The Android walkthrough is 52.2 seconds; the iOS walkthrough is 31.9 seconds. Those four verification movies are H.264 at 720 pixels wide and have been fully decoded after compression. They are actual virtual-device recordings, not mockups.

### Reels-style demos

The [iOS reel](../media/demos/ios-demo.mp4) and [Android reel](../media/demos/android-demo.mp4) are **30.5-second, 1080 x 1920, 60 fps** product edits. Ten short scenes combine kinetic Polish typography, animated camera moves, native UI detail crops, editorial wipes, official website artwork and an original procedural soundtrack. The visual direction follows the earlier [Klavi HTML-composition reference](https://lnkd.in/p/e4F-NJAc), using Bielik's own colors and fonts.

These are **edited recordings, not new inference runs or speed benchmarks**. Pauses and navigation are cut, and completed-reply footage is revisited for its detail shot. All moving native clips play at **1x**; opening/closing compositions also use still frames from the real recordings. Replies are not fabricated or retyped. Bielik inference remains on the Mac CPU, not the phone.

The unchanged [raw iOS screen recording](../media/demos/ios-raw.mp4) is 40.805 seconds; the [raw Android screen recording](../media/demos/android-raw.mp4) is 45.044 seconds. Neither has presentation overlays, music, cuts or speed changes. Their original [iOS](../media/demos/ios-raw.json) and [Android](../media/demos/android-raw.json) capture reports preserve recording hashes, prompts, untouched responses, native clipboard verification and device identity. Both were captured on October 6 using dedicated recording devices; the October 7 reel edit did not run the app, model, simulator or desktop automation again.

The reel [iOS report](../media/demos/ios-demo.json) and [Android report](../media/demos/android-demo.json) add exact source-to-output shot maps, rendering hashes and delivery properties. The [edit map](../scripts/reels/edit-map.json) is tied to the raw recording hashes. Its cuts are calibrated against visible movie frames rather than assuming the capture script's wall-clock chapter times exactly match the native recorder's media clock.

Reproduce the edits from the repository root with Python, FFmpeg and Playwright's **headless WebKit** renderer. No interactive browser window, Chromium video-compositor layer, XCTest or simulator is involved. Fonts and artwork load only from a temporary loopback server with an explicit resource allowlist. Decoded native images are painted into a deterministic HTML canvas; each delivered video frame is compared with its rendered reference to catch missing layers or tiled frames.

Install the optional rendering dependencies only if needed:

```bash
python3 -m pip install -r scripts/requirements-reels.txt
python3 -m playwright install webkit
```

```bash
python3 scripts/render-reels.py \
  --ios-recording media/demos/ios-raw.mp4 \
  --ios-report media/demos/ios-raw.json \
  --android-recording media/demos/android-raw.mp4 \
  --android-report media/demos/android-raw.json \
  --work-dir /tmp/bielik-reels/work \
  --output /tmp/bielik-reels/output
```

Add `--preview` to generate storyboard contact sheets without encoding videos. To intentionally replace the repository demos, use `--output media/demos --replace`. Other captures require their own `--edit-map`: the renderer rejects a map calibrated for different source hashes. Intermediate image frames are streamed through memory instead of saved as a large image-sequence directory; temporary encoding files and the server are cleaned up when the command exits.

The music is synthesized by [`soundtrack()`](../scripts/render-reels.py) at 120 BPM with original notes, percussion and transition sounds, then encoded as stereo AAC with a -16 LUFS normalization target. It contains no borrowed music, reference-video audio or generated speech. The [`composition.html`](../scripts/reels/composition.html) scene code and synthesis code are reproducible source, while the official Bielik artwork and bundled fonts retain the rights documented below.

## Release and physical phones

Release builds contain no DevFlow agent and no cleartext transport exceptions. Restore separately when changing configuration, because the Debug-only package references affect NuGet assets:

```bash
dotnet restore Bielik/Bielik.csproj -p:Configuration=Release
dotnet build Bielik/Bielik.csproj --no-restore --target:Rebuild \
  --framework net11.0-ios --configuration Release \
  -p:RuntimeIdentifier=iossimulator-arm64 \
  -p:EnableCodeSigning=true -p:CodesignKey=-

dotnet build Bielik/Bielik.csproj --no-restore \
  --framework net11.0-android --configuration Release \
  -p:RuntimeIdentifier=android-arm64 -p:AndroidPackageFormats=apk
```

Repeat the Debug restore before switching back to Debug. Both Debug and Release targets build with zero warnings or errors. The final Release apps were installed and cold-started on their respective virtual devices; both rendered the discovery screen, had no development agent, and retained their strict transport policy.

On a physical iPhone, `127.0.0.1` means the phone, **not the Mac**. Use a private-IP HTTPS reverse proxy on the same trusted LAN, with a valid certificate trusted by iOS, forwarding to loopback Ollama. Keep Ollama itself on loopback, do not expose either server to the internet, and do not disable certificate validation. Release rejects a previously saved HTTP address with an explicit error. Device provisioning requires your Apple signing identity.

On physical Android hardware, `10.0.2.2` is not the Mac gateway; use the same private-IP HTTPS approach with a certificate trusted by Android. The verified APK is ARM64. Release rejects saved HTTP endpoints at the shared policy layer and also sets `android:usesCleartextTraffic="false"`. Do not publish using the SDK's development signing key; configure your own release signing identity first.

Physical-device deployment, TLS provisioning, and App Store/Play Store distribution are not part of the verified virtual-device setup. There is no embedded 11B inference engine in this app.

## Privacy and implementation boundaries

Only the endpoint preference is persisted. Messages remain in memory; starting a new conversation, changing the endpoint, or restarting the process discards them. Only completed exchanges enter the next inference request, limited to the last five full exchanges plus the current question. Canceled and failed fragments remain marked in the UI but are excluded from future context.

The HTTP client disables proxies and redirects. Endpoints must be localhost, loopback, RFC1918 IPv4, or IPv6 unique-local addresses. Public addresses, credentials, query strings, non-root paths, and cloud-metadata addresses are rejected. Debug permits local HTTP for simulator development; Release requires HTTPS. The selected server is trusted to run the installed weights, so do not point it at an untrusted proxy. Ollama may retain diagnostic logs; the app does not configure a chat-history database.

Model-card links open external documentation only; they are not inference endpoints. Model-generated answers can be wrong and should be reviewed.

Sources: [Bielik](https://bielik.ai/), [Bielik locally](https://bielik.ai/bielik-lokalnie/), and the [official SpeakLeash model card](https://huggingface.co/speakleash/Bielik-11B-v2.6-Instruct-GGUF), which identifies the selected weights as Apache-2.0 licensed. Weights are downloaded separately and are not committed to this repository.

## License

Application source and original artwork are MIT-licensed; see [LICENSE](../LICENSE). The .NET template copyright notice is retained. The separately downloaded Bielik weights have their own Apache-2.0 license.

The official SpeakLeash logo is bundled locally, unchanged, from the project's [MIT-licensed Bielik prompt book](https://github.com/speakleash/bielik-prompt-book/tree/b1eb2591c08f7ddf2d111c8325c4dc7cff11b173). It appears in the discovery and model credits. Its copyright, exact source, and MIT notice are preserved in [the packaged third-party notices](../Bielik/Resources/Raw/third_party_notices.txt). No remote image requests are made by the app.

The Bielik website wordmark, eagle, neural-network illustration, gradient background and favicon are now bundled under the project owner's explicit authorization to use images from bielik.ai. Their original copyright and trademark rights remain with their owners; they are **not relicensed under the application's MIT license**. The model's Apache-2.0 license does not establish artwork rights. Exact sources and unchanged source-file hashes are in the [asset manifest](../Bielik/Resources/Raw/website_assets.json).

Geologica Regular/SemiBold and Source Sans Pro Regular/Semibold are bundled unchanged under SIL Open Font License 1.1. Full notices are packaged in [the Geologica license](../Bielik/Resources/Raw/licenses/geologica_ofl.txt) and [the Source Sans Pro license](../Bielik/Resources/Raw/licenses/source_sans_pro_ofl.txt). Names and trademarks remain with their owners; this application is not endorsed by SpeakLeash.
