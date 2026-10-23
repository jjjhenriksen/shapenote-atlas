# Native reader QA — 2026-10-22

This is a partial actual-native-window receipt for [issue #57](https://github.com/jjjhenriksen/shapenote-atlas/issues/57), awaiting human review. It does **not** close #57. The tested implementation is pinned to `ab147eac003303be5796ead93f6d059edeae63d5`; later fixes need their own head-specific native verification.

## Exact build and runtime

The documented `script/build_and_run.sh --verify` flow built the production reader assets and native executable. The isolated app was launched on macOS 26.6.2 (25G83), arm64. Only its app directory, `CFBundleIdentifier` and `CFBundleName` were renamed to avoid colliding with an existing user app; native executable and reader bytes were unchanged. Package verification was run again after that rename and passed.

| Identity | Value |
| --- | --- |
| Bundle identifier | `com.sacredharp.atlas-native-reader-qa-20261022` |
| Native executable SHA-256 | `8f7181bf5f589dba61a797580643777f66a9741cf9aeb065adf2959e7e419be6` |
| Assets manifest SHA-256 | `cfe50974bbb9656647b15aea7bf585242f36a0727238f19a7cbf65c6bcc0347f` |
| Bundle manifest SHA-256 | `de104d06b10e19afdc376a7e41d9b53cf6d0d7c486582581cb075d97ae0958e6` |
| Retained asset size | 6,723 files; 627,432,676 logical bytes |

Each private manifest is a path-sorted list of `{path, bytes, sha256}` records; its digest is over canonical JSON (`sort_keys=True`, separators `(',', ':')`, trailing newline). The bundle manifest excludes directory entries and covers all regular bundle files. The package was checked against those manifests after QA and remained unchanged. Full manifests, package, screenshots and raw accessibility evidence remain in the private evidence packet named `atlas-native-reader-qa-20261022`. [receipt.json](receipt.json) indexes permitted evidence hashes without embedding restricted content.

## Observed in the native window

| Check | Observation | Limit |
| --- | --- | --- |
| Lookup, score selection, rendering | Samaria SH1991 selected; production OSMD-backed reader visibly rendered a four-part score. | Rendered notation does not establish source correctness. |
| Pause, resume, stop | Pause and resume controls changed with advancing progress; stop restored Play and progress zero. | UI and audio clock were observed; audible output was not accepted. |
| Edition reference and source handoff | SH2025 Samaria retained its SH1991 witness notice; source link opened Safari at the expected `fasola.org/indexes/2025/?p=26`; native selection remained intact. | One destination was checked, not every source link or exact-edition engraving. |
| Encoded repeat setting | Kentucky New-Salem retained Review draft and unavailable key labels. Follow encoded repeats, two loops, tempo 220 produced advancing progress and automatic return to idle. | No key was inferred; exact sounded repeat order, loop count and audible duration remain unverified. |
| Source-only and prose policy | Weary Rest exposed no transposable score/practice controls. Three Amigos displayed prose/no score expected. | UI policy observation; raw source/PDF content is private. |
| Quit and reopen | The same bundle reopened the default reader. | Its old private server survived quit: [#512](https://github.com/jjjhenriksen/shapenote-atlas/issues/512). The old endpoint closed without a response. |
| Download | New-Salem's published MusicXML was available over HTTP, but the native click produced no save panel or saved file. | Reproduced [#511](https://github.com/jjjhenriksen/shapenote-atlas/issues/511); HTTP availability is not native save proof. |

For the repeat probe, progress reached 25% at 17.825 wall seconds and was idle by 86.575 seconds. The existing planner predicted 69.818 audio-clock seconds, but that is derived from the same implementation, not an independent audible measurement. The receipt preserves this distinction. Probe 17 selected the wrong record while Practice was active; only successful Library probe 18 supports the source-only observation.

## Runtime diagnostics and remaining acceptance

The first native app PID had 74 error-level unified-log records in the collected interval. Those include an AudioComponentRegistrar remote proxy lookup failure (`NSCocoaErrorDomain` 4099, “Operation not permitted”), alongside OS/AppIntents, WebKit and input/window diagnostics. Their application versus environment causes are not fully triaged. Empty captured stdout/stderr do not establish a clean runtime; JavaScript console and every WebContent process were not instrumented.

Human review still needs to resolve:

- Can the native app be heard on the intended output device, and does the audio diagnostic affect actual playback?
- Do encoded repeats, loops and notes sound correct against the exact permitted source witness?
- Does a fresh native launch work with networking genuinely disconnected and only the supported retained assets available? This run did not change global network settings or establish cold-cache offline behavior.
- After #511 and #512 land, do download and quit/reopen pass on their exact final implementation? This receipt remains pinned to the earlier tested commit.

`humanAccepted`, `sourceCertified` and `safeToPromote` remain false. Review draft assets retain their existing quarantine. There is no signing, notarization, distribution or deployment approval. Only the explicitly owned QA app and child processes were stopped; existing user apps were preserved.

## Reproduce the bounded checks

At the pinned commit, use private output locations with the documented build:

```sh
ATLAS_OUTPUT_DIR=<private>/package ATLAS_DIST_DIR=<private>/dist bash script/build_and_run.sh --verify
```

If isolating the app identity, rename only the app directory and its bundle identifier/name, then rerun `scripts/verify_startup.py` against that package and production dist. Hash the complete bundle and web directory before launch. In the native window, select Samaria SH1991, exercise Play/Pause/Resume/Stop, switch to SH2025 and open its source link, then select Kentucky New-Salem for the encoded-repeat settings. Inspect Weary Rest from Library and Three Amigos from Trumpet. Record the selected tune, visible labels, app/server ownership and actual destination rather than relying on build or browser-only results. Keep restricted screenshots/source content in private storage, and rehash the bundle after cleanup. This procedure supports the bounded observations above; it does not supply the remaining human acceptance.
