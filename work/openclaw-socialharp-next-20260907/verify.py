"""Verify additive map integrity; this does not substitute for visual source review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(ref):
    path = ROOT / ref['path']
    assert digest(path) == ref['sha256'], f'Changed input: {path}'
    return json.loads(path.read_text())


def main():
    data = json.loads((PACKAGE / 'socialharp-page-map-supplement-v2.json').read_text())
    baseline = checked(data['baseline'])
    assert baseline['summary'] == data['baseline']['summary']
    prior_rows = []
    for reference in data['previous_supplements']:
        prior_rows.extend(checked(reference)['records'])
    mapped = baseline['mapped_records'] + prior_rows
    mapped_ids = {row['record_id'] for row in mapped}
    assert len(mapped_ids) == len(mapped), 'Prior mappings overlap'
    remaining = [r for r in baseline['unresolved_records'] if r['record_id'] not in mapped_ids]
    rows = data['records']
    assert [r['record_id'] for r in rows] == [r['record_id'] for r in remaining[:5]]
    assert len({r['record_id'] for r in rows}) == 5
    assert not mapped_ids.intersection(r['record_id'] for r in rows)
    assert digest(ROOT / data['source']['path']) == data['source']['sha256']
    for row, original in zip(rows, remaining):
        assert row['song_no'] == original['song_no']
        assert row['catalogue_title'] == original['title']
        assert row['literal_heading'].removesuffix('.') == original['title']
        assert row['printed_page'] == original['song_no']
        assert isinstance(row['pdf_leaf_1_based'], int) and row['pdf_leaf_1_based'] > 0
        assert row['source_pdf'] == data['source']['path']
        assert row['scan_sha256'] == data['source']['sha256']
        assert digest(ROOT / row['render']) == row['render_sha256']
        assert row['notation_imported'] is False
        assert row['exact_edition_notation_verified'] is False
    summary = data['summary']
    assert summary['previous_combined_mapped'] == len(mapped)
    assert summary['previous_combined_unresolved'] == len(remaining)
    assert summary['combined_mapped'] == len(mapped) + len(rows)
    assert summary['combined_unresolved'] == len(remaining) - len(rows)
    assert summary['combined_mapped'] + summary['combined_unresolved'] == baseline['summary']['catalogue_records'] == summary['catalogue_records_unchanged']
    print(json.dumps(dict(result='pass', reviewed_source_identities=len(rows), combined_mapped=summary['combined_mapped'], combined_unresolved=summary['combined_unresolved'], originals_unchanged=True, notation_imported=False)))


if __name__ == '__main__':
    main()
