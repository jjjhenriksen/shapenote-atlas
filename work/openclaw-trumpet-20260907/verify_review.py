"""Check review coverage, retained bytes, and preservation; not a visual oracle."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path(__file__).with_name('trumpet-page-identity-review-v1.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    review = json.loads(REVIEW.read_text())
    prior_path = ROOT / review['predecessor_map']
    assert digest(prior_path) == review['predecessor_sha256'], 'Predecessor changed'
    prior = json.loads(prior_path.read_text())
    assert digest(ROOT / review['source_pdf']) == review['source_sha256'], 'Source changed'
    preserved = json.dumps(prior['mapped_records'], sort_keys=True, separators=(',', ':'))
    assert hashlib.sha256(preserved.encode()).hexdigest() == review['preserved_mapped_records_sha256']
    assert len(prior['mapped_records']) == review['summary']['previously_mapped_preserved'] == 95
    old = {r['record_id']: r for r in prior['unresolved_records']}
    rows = review['reviewed_records']
    assert len(rows) == len(old) == 10
    assert {r['record_id'] for r in rows} == set(old), 'Omitted or invented target'
    assert not ({r['record_id'] for r in rows} & {r['record_id'] for r in prior['mapped_records']})
    for row in rows:
        original = old[row['record_id']]
        assert row['pdf_leaf'] == original['candidate_pdf_page']
        assert row['catalogue_title'] == original['title']
        assert digest(ROOT / row['render_path']) == row['render_sha256'], 'Render changed'
        assert row['literal_headings'] and row['printed_page']
        assert row['notation_imported'] is False and row['canonical_record_changed'] is False
        if row['content_kind'] == 'prose':
            assert row['source_title'] is None and row['resolution'] == 'not-a-notation-page'
        else:
            assert row['content_kind'] == 'notation' and row['source_title']
    counts = Counter(r['resolution'] for r in rows)
    assert counts['literal-title-match'] == review['summary']['literal_title_matches'] == 4
    assert counts['catalogue-title-correction'] == review['summary']['catalogue_title_corrections'] == 3
    assert counts['not-a-notation-page'] == review['summary']['prose_only_pages'] == 3
    print('PASS: 10/10 leaves reviewed; 95 prior mappings and all source/render bytes preserved; 7 notation-page identities, 3 prose pages; no notation imported.')


if __name__ == '__main__':
    verify()
