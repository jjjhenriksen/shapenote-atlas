"""Verify package integrity and merge invariants; visual truth requires scan review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    data = json.loads((PACKAGE / 'socialharp-page-map-supplement-v1.json').read_text())
    baseline_path = ROOT / data['baseline']['path']
    assert digest(baseline_path) == data['baseline']['sha256'], 'Baseline changed'
    baseline = json.loads(baseline_path.read_text())
    assert baseline['summary'] == data['baseline']['summary']
    assert digest(ROOT / data['source']['path']) == data['source']['sha256'], 'Source changed'
    rows = data['records']
    original = baseline['unresolved_records'][:len(rows)]
    assert [r['record_id'] for r in rows] == [r['record_id'] for r in original]
    prior_ids = {r['record_id'] for r in baseline['mapped_records']}
    assert len({r['record_id'] for r in rows}) == len(rows)
    assert not prior_ids.intersection(r['record_id'] for r in rows)
    for row, old in zip(rows, original):
        assert row['catalogue_title'] == old['title']
        assert row['song_no'] == old['song_no']
        assert row['literal_heading'].removesuffix('*').removesuffix('.') == old['title']
        assert row['printed_page'] == old['song_no']
        assert isinstance(row['pdf_leaf_1_based'], int) and row['pdf_leaf_1_based'] > 0
        assert row['source_pdf'] == data['source']['path']
        assert row['scan_sha256'] == data['source']['sha256']
        assert digest(ROOT / row['render']) == row['render_sha256'], 'Evidence render changed'
        assert row['notation_imported'] is False
        assert row['exact_edition_notation_verified'] is False
    summary = data['summary']
    assert summary['combined_mapped'] == len(prior_ids) + len(rows)
    assert summary['combined_unresolved'] == len(baseline['unresolved_records']) - len(rows)
    assert summary['combined_mapped'] + summary['combined_unresolved'] == baseline['summary']['catalogue_records']
    print(json.dumps({'result': 'pass', 'reviewed_source_identities':len(rows), 'combined_mapped':summary['combined_mapped'], 'combined_unresolved':summary['combined_unresolved'], 'original_map_sha256':digest(baseline_path), 'notation_imported':False}))

if __name__ == '__main__':
    main()
