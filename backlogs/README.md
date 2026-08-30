# Sacred Harp adversarial-audit backlog

These are independent worker packets derived from the pasted adversarial audit. Each worker should receive the `/goal` text in its packet and work only inside that packet's ownership boundary.

## Dispatch order

| Priority | Packet | Owns |
| --- | --- | --- |
| P0 | `01-transcribe-2025/BACKLOG.md` | The 90 missing 2025 scores |
| P0 | `02-key-mode/BACKLOG.md` | Major/minor authority and unknown keys |
| P0 | `03-review-semantics/BACKLOG.md` | Contradictory human-review dispositions |
| P1 | `04-correction-needed/BACKLOG.md` | The 13 source-aligned but incomplete records |
| P1 | `05-semantic-fidelity/BACKLOG.md` | Corpus-wide note/measure/lyric/repeat fidelity |
| P1 | `06-shapes/BACKLOG.md` | Source-faithful four-shape verification |
| P1 | `07-browser-audio/BACKLOG.md` | Real browser playback proof |
| P1 | `08-edition-reconciliation/BACKLOG.md` | Full 1991/2025 shared-song diffs |
| P2 | `09-additions-queue/BACKLOG.md` | 2025 additions/queue overlap invariants |
| P2 | `10-source-health/BACKLOG.md` | Reachability and source-integrity checks |
| P2 | `11-startup-deployment/BACKLOG.md` | Clean startup and packaged-app smoke test |
| P2 | `12-reproducible-validation/BACKLOG.md` | One reproducible verification entry point |

## Shared rules

- Treat the current checkout as dirty and user-owned. Inspect before editing; never reset, clean, or overwrite unrelated work.
- Immutable source images, scans, source MusicXML, and existing provenance manifests are authoritative and must be preserved.
- Never promote an OMR, imagegen, cross-edition, or inferred result as exact notation without direct source evidence.
- Keep `source-verified`, `source-observed`, `omr-detected`, and `unknown` semantically distinct.
- A blocked/rejected result is valid only when its reason is precise, record-specific, and represented in the canonical ledger.
- Do not edit `src/main.jsx` or `src/styles.css` from these data-audit packets unless a packet explicitly owns that surface.
- Run the packet's focused checks and report exact counts, files, and remaining uncertainty.
