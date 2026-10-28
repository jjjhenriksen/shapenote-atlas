# Reader before/after benchmark

Before: 9ecdc1bb5697dc83c619864160288e4b70aafe9e
After: 98a42e3bf05aa0212f6fdb49849d55de9835bfe7

3 cold-browser samples per build per viewport; 1.6 Mbps download, 150 ms latency, 4× CPU slowdown; identical gzip production server.

| Viewport | Metric | Before median (range) | After median (range) | Speedup |
|---|---|---:|---:|---:|
| desktop | catalogueMs | 3.77 s (3.64–3.81) | 3.64 s (3.57–3.84) | 1.04× |
| desktop | playableMs | 4.25 s (4.08–4.27) | 4.12 s (4.02–4.32) | 1.03× |
| mobile-viewport | catalogueMs | 3.64 s (3.63–3.64) | 3.60 s (3.57–3.72) | 1.01× |
| mobile-viewport | playableMs | 4.08 s (4.08–4.08) | 4.04 s (4.00–4.18) | 1.01× |

Catalogue: first animation-frame sample with selected tune heading and a visible catalogue row. Playable: visible enabled Play song button; not first audible sound.

Search round trip includes automation overhead; JSON byte snapshots include only resources completed at playback readiness, not all eventual traffic. See raw samples for individual requests.

Local production builds; mobile viewport, not mobile hardware; remote HTTPS blocked; server/disk caches warm; no audio or engraving-speed claim.

Small-sample lab results, not statistical significance or field Core Web Vitals. Every measured sample also checks identity, nonblank content, overlay, application errors, engraving readiness and search results.

## Interrupted-run recovery

The first process stopped after 10 of 12 samples. Those saved samples and exact
committed builds were retained. `--resume --reuse-builds` completed only the two
missing samples after checking revision, run count, browser, Node, OS, CPU and
compression metadata. The interruption separates the final pair in time; these
are exploratory results, not a statistical performance guarantee. No user-facing
30-second-to-4-second speedup is claimed: that comparison mixes development and
production servers. Versioned packing is a transport-byte reduction, with only a
small observed timing gain under gzip.
