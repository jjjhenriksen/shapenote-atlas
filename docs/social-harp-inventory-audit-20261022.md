# Social Harp inventory: bounded visual audit, draft

This is partial source-evidence work for
[Atlas #54](https://github.com/jjjhenriksen/shapenote-atlas/issues/54).
**`inventoryReconciled=false`; human review required.** It makes no catalogue,
notation, source-certification, publication or promotion change. It does not
identify or invent an additional tune, and does not close the count discrepancy.

## What was already known

Earlier identity accounting found 221 catalogue starts across 201 physical
leaves, including 20 shared-page pairs, from disjoint 67-entry baseline and
154-entry supplement mappings. That work is historical context here, not fresh
source proof from this audit. Its recorded input pins are:

- Baseline map: `8b30106fb48d2467d70063d684ac144887b02e3cfec4470da103dc13d2c90963`.
- v19 supplement: `1acdcd5a62598c63d87f6d6af466f7064d816487abd1e753685bcbf8f53c291e`.

The coordinator retrieved the [primary UGA Press book record](https://www.ugapress.org/9780820331515/the-social-harp/)
through the web tool at approximately 2026-10-23 06:07 UTC (2026-10-22 locally).
The tool reported a crawl from the prior week; this was not a new raw HTTP
capture. Its description attributes 222 pieces to the 1855 book, mostly
folktune settings, but supplies no operational counting definition or reason
for 221 catalogue records. The listed modern facsimile has 296 pages, including
introductory/appendix material; that pagination must not be subtracted from the
retained original scan's 254 physical leaves to infer missing music. No separate
printed index was recovered for exhaustive index-to-catalogue reconciliation.
Neither catalogue identity agreement nor a missing extracted header proves an
additional piece.

## Frozen source and first cohort

The retained source is a 254-leaf scan, 15,629,340 bytes, SHA-256
`562db348cf414b27c0c3e40da38cca0a8c39a11f2007abec370f9ddcae1bc331`.
The scan and full-page 180-DPI Poppler PNGs stay in ignored/private storage.
Physical PDF leaves are **one-based**; zero-based API index is `leaf - 1`.
Poppler `-f/-l` use the one-based leaf. Printed page labels are read separately;
for the four initial targets the directly checked printed Arabic labels equal
the physical leaves. No general offset is inferred for the whole scan.

Before reader dispatch, the source, rendered images, task, coordinate convention,
selected scope, reading schema and comparison rule were frozen in protocol
`2a1e0e65a051f36e873c416d2c02a4f21c205726bbf72a4aeb4a4d72811b4d05`.
Targets were leaves 206, 234, 244 and 247, with adjacent context 205, 207, 233,
235, 243, 245, 246 and 248. Two fresh source-only contexts received the pinned
packet and separate private output directories. They received no catalogue
maps, previous heading labels, prior reader observations, or expected inventory
outcome. Both reported inspecting every listed image. This is instruction-level
context separation, not an operating-system access attestation or independent
accuracy evaluation. Coordinator/OCR exposure remains explicit.

Both readings and reader metadata were hash-checked and made read-only before
comparison. The comparison implementation was committed before consuming the
readings. The [aggregate first-cohort receipt](experiments/social-harp-inventory-20261022-v1.json)
retains source/protocol/reading hashes and source coordinates while omitting raw
headings, lyrics and visual evidence.

Both readers classify all four target leaves as continuation-only, and their
literal heading signatures agree under the predeclared whitespace/case rule.
This supports treating those four missing extracted headers as a bounded
extraction gap rather than evidence of four new openings. It does not settle
the catalogue count. All twelve leaves remain marked unresolved because reader
uncertainties are retained; four adjacent-context leaves also have literal
heading disagreements. Those observations have not been reread, silently
corrected or rescored for nicer agreement.

## Separate development expansion

The remaining 33 selected targets were frozen separately under protocol
`bc75a42728469e7709d861512777d62f2c62ac31ba7c3f2b225db34b0ddbc84a`,
with 42 context images (75 physical leaves total). The original four targets
were excluded from this packet entirely. Prior-context overlap was limited to
leaves 233, 235, 243, 245, 246 and 248 and is explicitly recorded as development
exposure. Printed labels were left unknown in the plan where they had not been
visually established; readers supplied their own literal observations.

Two additional fresh source-only contexts inspected the full packet, with no
catalogue labels, expected inventory count or prior reading results. Their
readings and metadata were frozen before comparison. The
[development receipt](experiments/social-harp-inventory-20261022-development-v2.json)
retains the complete aggregate result. This is a DEVELOPMENT cohort, not a
held-out accuracy test; coordinator and earlier OCR exposure remain explicit.

Both readers classify all 33 selected targets as continuation-only, with matching
literal heading signatures under the frozen rule. Their page dispositions agree
across all 75 images, but literal context headings and uncertainties still need
review. Six targets (232, 243, 245, 246, 248 and 254) retain uncertainties; 44
physical leaves overall remain unresolved by the conservative receipt rules.
The original first-cohort receipt remains unchanged; no consumed observation was
silently repaired or rescored for nicer agreement.

Across the two validated protocols, the union is 81 distinct physical leaves.
Within the coordinator-proposed candidate music range 17–254, 157 leaves have
not yet been inspected by this census. These coverage figures come from the
actual frozen protocols and complete reader coverage, not catalogue counts.
A next bounded development proposal is targets 17–32 (16 leaves), with source
context leaves 16 and 33. Further dispatch requires capacity coordination and
its own frozen protocol. No further census has been performed by this draft.

## Read-only audit command

```sh
python3 scripts/audit_social_harp_inventory.py /private/run/source-packet \
  --expected-protocol-sha256 FROZEN_PROTOCOL_HASH \
  --reader-a /private/run/reader-a/reading.json \
  --expected-reader-a-sha256 FROZEN_READER_A_HASH \
  --reader-b /private/run/reader-b/reading.json \
  --expected-reader-b-sha256 FROZEN_READER_B_HASH
python3 -m unittest discover -s tests -p test_social_harp_inventory_audit.py -v
```

The command verifies exact protocol/source/image/reading hashes, coordinate
conversion and complete selected-leaf coverage. It requires distinct declared
reader IDs, enumerated opening headings for opening dispositions, normalized
heading coordinates, explicit continuation evidence and uncertainties. Hashes
are consistency pins, not signatures or evidence that readers obeyed their
instructions. An uncertain heading role requires an explicit page uncertainty,
so matching uncertain roles cannot disappear from the unresolved list. Printed
page labels must be present, with explicit null allowed when unknown. The
supplied protocol's page count is not independently parsed
from the PDF by this stdlib tool.

Comparison uses page disposition, literal printed label, and `(role, heading)`
with whitespace normalization and casefold only. Punctuation differences stay
disagreements. Coordinates are retained privately and checked for shape/range;
they are not an accuracy score. Any disagreement, uncertain disposition or
per-page uncertainty leaves the page unresolved. The aggregate emits only
counts, hashes, coordinates and disagreement categories. It never emits raw
headings or lyrics, edits an input, stages a score or changes catalogue data.

Exit 0 means a bounded comparison receipt was produced, including unresolved
results. Exit 2 means unavailable, malformed, mismatched or incomplete inputs.
All receipts keep `wholeBookReviewed=false`, `inventoryReconciled=false`,
`sourceCertified=false`, `safeToPromote=false`, `readerIndependenceVerified=false`
and `humanReviewRequired=true`.

## Remaining reconciliation

A full source-opening census still needs the remaining candidate music leaves
in manageable, separately frozen development cohorts. Preserve both existing
runs, prior-context/coordinator/OCR exposure and all uncertainties; do not reread
consumed targets solely for better agreement. No such cohort is a held-out test.

Exhaustive source/index coverage, treatment of multi-page works and alternate
counting units, and the publisher's piece-count definition remain unresolved.
Any eventual metadata correction needs a canonical, regeneration-safe source
with stable IDs, unchanged unrelated records and retained provenance. This draft
contains no such correction and must not be automatically merged as count
reconciliation.
