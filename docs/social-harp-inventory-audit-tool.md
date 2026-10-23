# Read-only frozen source-reading audit

`scripts/audit_social_harp_inventory.py` compares two declared, pinned visual
readings and emits an aggregate receipt. It supports the engineering workflow
in [#517](https://github.com/jjjhenriksen/shapenote-atlas/issues/517).
Real source observations and human inventory decisions belong in the separate
[draft source review](https://github.com/jjjhenriksen/shapenote-atlas/pull/513).
This tool makes no catalogue, notation, staging or publication changes.

```sh
python3 scripts/audit_social_harp_inventory.py /private/run/source-packet \
  --expected-protocol-sha256 FROZEN_PROTOCOL_HASH \
  --reader-a /private/run/reader-a/reading.json \
  --expected-reader-a-sha256 FROZEN_READER_A_HASH \
  --reader-b /private/run/reader-b/reading.json \
  --expected-reader-b-sha256 FROZEN_READER_B_HASH
python3 -m unittest discover -s tests -p test_social_harp_inventory_audit.py
```

The source packet contains `protocol.json`, `source.pdf` and listed
`leaf-NNN.png` images. Schema version 1 uses kind
`social-harp-source-only-inventory-protocol`, source SHA-256/byte length/page
count, coordinates `{pdfLeafBase: 1, pdfIndexBase: 0}`, target physical leaves,
and unique page entries with leaf/index/image filename/image SHA-256. A physical
leaf converts to a zero-based index with `index = leaf - 1`; printed labels are
independently declared. The supplied page count is not parsed from the PDF.
The tool checks exact file pins, not that an image was rendered from its claimed
page or that anyone followed the source-reading instructions.

Each reading has kind `social-harp-source-only-inventory-reading`, schema
version 1, a distinct declared reader ID, protocol/source pins, complete unique
page coverage and notes. Each page requires a leaf/index, an explicit printed
label (string or null), disposition, enumerated headings, continuation evidence
or uncertainty, and an uncertainty list. Headings carry literal text, role and a
nondegenerate normalized `[x0,y0,x1,y1]` box. Dispositions are opening-present,
continuation-only, mixed, non-music or uncertain; roles are opening,
continuation, other or uncertain. Opening dispositions require an opening
heading; continuation-only/non-music forbid one. An uncertain heading role
requires an explicit page uncertainty. Invalid or missing fields fail closed.

The aggregate keeps existing total `headingCounts` and adds per-page
`headingRoleCounts`, a pair of count objects ordered reader A then reader B,
matching `readerSha256`. Each object separately contains `opening`,
`continuation`, `other` and `uncertain`, including zeros. For a **synthetic**
page with two declared openings, one continuation, one section heading and one
uncertain heading, each agreeing reading reports counts `2/1/1/1`. The tool
counts supplied roles; it does not classify images, infer missing headings,
deduplicate musical works or decide a publisher's meaning of “piece.” Context
pages remain marked separately from targets. Repeated context across runs must
not be summed as new source coverage.

Comparison retains page-disposition, literal printed-label and heading-signature
disagreements. Heading normalization only folds case and whitespace; punctuation
stays meaningful. Matching role counts cannot resolve a title disagreement.
Any disagreement, uncertain disposition or page uncertainty retains the leaf in
`unresolvedLeaves`. Aggregate output omits raw headings, lyrics, visual notes
and evidence images. Input error text may include local paths; keep processing
receipts private when those locators are sensitive.

`processingVersion=2` identifies the role-count processing format;
`processorSha256` hashes the helper file read when generating the receipt. That
pin is not a process/execution attestation. Retain an external commit/file pin
when freezing a run. If a later helper processes an older frozen protocol,
retain the original protocol/code identity and raw freezes, and write a new
derived receipt plus a manifest binding the new processing version/helper pin.
Never overwrite earlier receipts to hide a processing change. The synthetic
tests use placeholder PDF/image bytes and do not establish visual correctness.

Exit 0 means a bounded receipt was produced, potentially with unresolved pages.
Exit 2 means unavailable, malformed, mismatched or incomplete inputs. Every
successful receipt has `readerIndependenceVerified=false`,
`wholeBookReviewed=false`, `inventoryReconciled=false`, `sourceCertified=false`,
`safeToPromote=false` and `humanReviewRequired=true`. Declared counts and hash
consistency confer no source, acceptance, counting-policy, rights or publication
authority.
