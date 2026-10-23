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

At the end of those first two cohorts, the validated protocol union was 81
physical leaves within the coordinator-proposed candidate music range 17–254,
with 157 not yet covered. Those figures are retained as that processing point's
coverage, not a catalogue count.

## Development v3: physical leaves 17–32

The third packet froze targets 17–32 and context 16 and 33 under protocol
`6a2c41bf9659d565775f81213dd1bbe2177c62ceb8cb0287027ad226359e4711`.
Context leaf 16 is outside the candidate music span. Two fresh source-only
contexts inspected all 18 images. Both complete readings and metadata were
hash-checked and made read-only before either reading was disclosed or compared.

The [separate v3 receipt](experiments/social-harp-inventory-20261022-development-v3.json)
uses processing version 2 and retains all pins, per-reader role counts and
unresolved leaves. All 16 targets agree as opening-present, with matching literal
heading signatures under the frozen rule. Each reading declares 21 opening
headings and two other headings across those targets. These are supplied-role
counts, not a count of accepted musical works or a publisher's pieces. Target
leaf 17 and context leaf 33 remain unresolved from retained reader uncertainty;
no observation has been repaired or rescored. All 18 page dispositions, printed
labels and literal heading signatures agree, which does not resolve uncertainty.

Reader A was prematurely interrupted by the coordinator to request progress
while its authoritative state was RUNNING, then resumed in the same context with
its own observations preserved. It reported all 18 images inspected and no
content effect from that technical interruption. No replacement reader or other
reading was supplied. The interruption and instruction-level isolation limits
remain evidence limitations, with no independent process attestation. Frozen
metadata pins are `30408d3576e5f76829ac661c5eb850b6fdda9be688e4e5d2b53d456fb51cdda2`
and `9665bbfaba1be6d4bf0582ccd8ad45c3692da43e39344f229ecf31d4ec97a9f4`.

The role-count implementation was committed and separately pinned after reader
dispatch but before any v3 observation disclosure. Old/new processing snapshots
and both new derived directories are retained; removing the added version/hash
and role-count fields makes the new result identical to the old processing
result. The frozen protocol, source and raw readings remain unchanged. This is
development evidence, with coordinator/OCR exposure explicit, not a held-out test.

At the end of v3, completed protocol coverage was 98 distinct candidate physical
leaves, leaving 140 not yet covered. Context leaf 16 was excluded. Those figures
are retained as the third-cohort processing point.

## Development v4: sixteen further targets

The fourth packet froze targets 34, 41–44 and 48–58, with adjacent context
33, 35, 40, 45, 47 and 59: 22 images under protocol
`672414eab84560b9f02383170036b70cc35230dd5716e9743476c8513c5ae5eb`.
The source and processing-version-2 implementation were pinned before either
fresh source-only context inspected the packet. Both complete readings and
metadata were jointly hash-checked and made read-only before disclosure or
comparison. Metadata pins are
`63c65bce0e18eefccb4a0cf27d781f72de0e5a358c527996893ad0115899ba9e`
and `772e184d17923a79bd083f9a87b8156c349a368fe9f64ffaa2a80ea412a73c04`.

The [separate v4 receipt](experiments/social-harp-inventory-20261023-development-v4.json)
records all 16 targets as agreed opening-present, with 19 declared opening
headings and one other heading per reader across those targets. All 22 page
dispositions, printed labels and literal heading signatures agree, with no
page uncertainties recorded in this cohort. Its empty unresolved list does not
clear any earlier uncertainty or disagreement, including repeated context leaf
33. Earlier raw readings and receipts remain unchanged; no majority selection
or retrospective correction was applied.

All targets were new to completed coverage. Five contexts (33, 35, 40, 45 and
47) repeat previous source material to support adjacent new targets; those
observations were not supplied to the fresh readers. Context 59 adds new source
coverage. Coordinator/OCR exposure and development status remain explicit; this
is not a held-out test or source certification. A coordinator metadata preflight
initially expected a different inspected-leaf key; the recorded correction reads
the existing `actualInspectedPhysicalLeaves` field without modifying either
frozen metadata file or reading. It does not change source observations.

Across four complete paired-reading protocols, 115 distinct physical leaves
within candidate span 17–254 are covered, with 123 not yet covered. Context leaf
16 remains separate. These figures use the actual protocol union after
comparison, not catalogue counts. The next prepared bounded proposal has new
targets 60–62, 66–70 and 74–81, with adjacent context 59, 63, 65, 71, 73 and 82:
22 images. Reader dispatch still requires coordinated capacity; no next-cohort
observations are included here. Declared headings remain distinct from accepted
musical works and the unresolved publisher counting unit.

## Engineering separation and processing versions

The generic read-only helper, synthetic tests and CI registration are now on
main through [engineering PR #518](https://github.com/jjjhenriksen/shapenote-atlas/pull/518),
with [source-free tool documentation](social-harp-inventory-audit-tool.md).
This human-review draft retains the original source receipts and history.

The original public/private receipts and raw freezes remain byte-for-byte
unchanged. New private derived directories process those same two frozen
readings with helper commit `4a3d6bc5f464d4d34fd6378c59a4214457e4bcbc`,
processing version 2, SHA-256
`6b03c7c2ac840cf54304d6062ce200e9cb2573e46df608cc7123372ed2b9d6a8`.
The [separate derivation receipt](experiments/social-harp-inventory-processing-v2-20261022.json)
binds old/new aggregate hashes and adds per-reader counts for declared opening,
continuation, other and uncertain heading roles. Every previous comparison
field is unchanged. Both readers declare zero opening headings on the 37
selected continuation targets. This counts supplied roles; it does not resolve
uncertainty, count unique musical works or establish a publisher's piece unit.
Prior-context overlap must not be summed as new coverage.

The first-two-cohort derivation receipt excludes v3 observations; v3 has its own
separate receipt above. Processing version 2 and development cohort v2 are
separate labels. All original source/protocol/raw freezes retain their identities.

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
