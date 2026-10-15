# Matched reader startup benchmark

## Recorded comparison (2026-10-14)

All 20 measured loads passed: five samples per build and viewport, comparing
`00cf5e2618023674b6857e9900000d94ad2dcf63` with
`be7fb4f810157ee43901f76a40b0831b7387deb8` under the protocol below.

| Viewport | Readiness | Before median | After median | Speedup |
| --- | --- | ---: | ---: | ---: |
| Desktop | Catalogue | 21.71 s | 3.64 s | 5.97× |
| Desktop | Playback | 21.93 s | 4.07 s | 5.39× |
| Mobile-sized | Catalogue | 21.77 s | 3.64 s | 5.97× |
| Mobile-sized | Playback | 21.98 s | 4.09 s | 5.37× |

These are local production-build measurements, not real-device or deployed-host
results. Raw artifacts from this run were saved locally under
`/tmp/atlas-reader-benchmark-20261014`; they are not committed or durable hosting.

## Rerun

Run from the repository after `npm ci`, with Chrome installed:

```sh
npm run benchmark:reader -- --before 00cf5e2 --after be7fb4f --runs 5 --out /tmp/atlas-reader-benchmark
```

Use explicit commit refs so the comparison remains stable after new commits.
Defaults are `HEAD^` and `HEAD`. Both committed dependency locks must match the
installed checkout's lock; dependency changes need separately installed snapshots.
No new dependencies are installed by the benchmark. Browser plugin was unavailable
when this harness was created; it uses the existing Playwright package and Chrome.

The command archives exact committed trees, builds both with the same installed
dependencies and Node runtime, and serves them with the same gzip-level-6 HTTP
server. It does not check out or modify either source revision. Build snapshots,
logs, screenshots, metadata, individual samples, summary JSON and a Markdown
report go under `--out`, outside committed source by default. Snapshots are large:
allow several GB for the corpus and production output. Existing build directories
are not overwritten. To rerun against verified saved builds:

```sh
npm run benchmark:reader -- --before 00cf5e2 --after be7fb4f --runs 5 --out /tmp/atlas-reader-benchmark --reuse-builds
```

Rerunning replaces report/sample/screenshot files in that output directory.
`--channel chromium` selects installed Playwright Chromium instead of Chrome.

## Protocol and interpretation

- The same Kentucky New-Salem deep link is used on both builds.
- Desktop 1440×1000 and mobile-sized 390×844 viewports; **not physical mobile devices**.
- 1.6 Mbps download, 150 ms latency, 4× CPU slowdown through Chromium CDP.
- Fresh isolated browser context for every sample; HTTP cache disabled and service
  workers blocked. Local server/disk/compression caches and browser process are warm.
- Excluded unthrottled warmup per build. Runs are sequential; before/after order
  reverses every pair. No parallel runs competing for network/CPU.
- Remote HTTPS fonts/source sites are blocked on both builds. Local app payloads
  are real, not mocked. HTTP failures, local failed requests and application errors
  fail the run instead of silently becoming fast samples. Intentional obsolete
  fetch cancellations (`net::ERR_ABORTED`) are retained separately, not failures;
  the selected tune still has to reach playable and engraved states.
- Catalogue ready: animation-frame sample observing selected tune heading and a
  visible result row. Playback ready: visible enabled **Play song** button. These
  navigation-relative timestamps do not measure first audible output or engraving.
- Every run also verifies page identity, nonblank content, no framework overlay,
  completed engraving and a search returning the expected single tune. The first
  sample of each build/viewport gets a screenshot.
- Search timing includes Playwright overhead and is a diagnostic, not a pure
  application interaction latency metric.
- Resource timing captures completed downloads at playback readiness. This is a
  readiness snapshot, **not total eventual traffic**, and decoded JSON bytes are
  not network transfer bytes. Raw samples retain encoded, decoded and transfer sizes.
- Report median, range and raw samples; JSON also includes nearest-rank p95.
  With five samples p95 is just the maximum. No significance or field-performance
  claim follows from this small local experiment. Compression and the fixed tune
  matter; don't extrapolate to all hosts/tunes, playback speed or engraving speed.

If a run fails, partial samples remain available, but no completed comparison
should be claimed. Check `status.json` for the latest attempt's status, especially
after reusing builds. A successful command writes `report.md` after all samples pass.
