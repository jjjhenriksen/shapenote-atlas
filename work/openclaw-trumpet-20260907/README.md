# Trumpet page identity review - 2026-09-07

Completed the ten-leaf page-identity batch in the OpenClaw program handoff. Every retained render was directly visually inspected in this review. This is a supplemental source-identity map, not a notation transcription or a claim that all songs are complete.

| PDF leaf | Printed page | Literal heading (meter omitted here) | Resolution |
| --- | --- | --- | --- |
| 116 | 69 | JOSHUA | Catalogue `Chris` is composer-credit contamination |
| 125 | 78 | LAMB OF GOD / ALLEGHENY | Catalogue lyric fragment belongs under upper LAMB OF GOD; two separate scores |
| 139 | vi | Three Amigos | Prose article, not a notation page |
| 187 | iv | Mr. Jeff Sheppard and a Brief Untrue History of the Rocking Chair Convention | Prose article; catalogue contains byline fragment |
| 20 | 12 | Lincoln Street | Literal title match; continuation beyond this leaf remains |
| 265 | iv | Old Paths: Nehemiah Shumway | Prose article, not a notation page |
| 42 | 25 | EUCLID | Literal title match in lower score; upper system is a continuation |
| 45 | 28 | New Canada | Catalogue incorrectly includes separate `C Major` text in title |
| 47 | 30 | TRAV’LER’S REST - SAMSON | Literal title match |
| 74 | 43 | ASHLEY | Literal title match in lower score; upper system is a continuation |

## Artifacts and verification

- `trumpet-page-identity-review-v1.json` records exact predecessor IDs, printed page versus PDF leaf, literal headings, title-correction rationale, source/render hashes and publication boundaries.
- `verify_review.py` checks full ten-record coverage, exact predecessor and source bytes, each retained render, all 95 preserved mapping records, and coherent prose/notation classification.
- `renders/` contains the unchanged, previously rendered ten leaves. The verifier requires these local retained evidence files and the original source PDF/map; this package does not duplicate or upload the PDF.

Run from the repository root:

```sh
python3 work/openclaw-trumpet-20260907/verify_review.py
```

Result: PASS. Four direct title matches, three source-backed title corrections, three prose-only pages. Zero target leaves remain uninspected. No existing map, canonical corpus record, score, pitch, lyric, shape, or key field was changed. The automated verifier proves preservation and structural coverage; direct visual inspection supplies the identity evidence.

## Ready next action

Use the four direct title matches and three explicit title corrections in a separately scoped catalogue/source-link update. Treat leaves 139, 187 and 265 as catalogue-cleanup candidates, not missing notation to invent. Preserve their existing IDs/history if reclassifying. The historical map still contains its original 95 matches and ten unresolved rows; this supplement resolves the review task without silently rewriting that history. No additional structured-score coverage is claimed.
