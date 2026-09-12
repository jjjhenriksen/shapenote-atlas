"""Verify additive map integrity; this does not substitute for visual source review."""
import hashlib
import json
import re
import struct
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
    data = json.loads((PACKAGE / 'socialharp-page-map-supplement-v9.json').read_text())
    baseline = checked(data['baseline'])
    assert baseline['summary'] == data['baseline']['summary']
    prior_rows = []
    for reference in data['previous_supplements']:
        prior_rows.extend(checked(reference)['records'])
    mapped = baseline['mapped_records'] + prior_rows
    mapped_ids = {row['record_id'] for row in mapped}
    assert len(mapped_ids) == len(mapped), 'Prior mappings overlap'
    remaining = [row for row in baseline['unresolved_records'] if row['record_id'] not in mapped_ids]
    rows = data['records']
    assert [row['record_id'] for row in rows] == [row['record_id'] for row in remaining[:10]]
    assert len({row['record_id'] for row in rows}) == 10
    assert not mapped_ids.intersection(row['record_id'] for row in rows)
    assert digest(ROOT / data['source']['path']) == data['source']['sha256']

    # Distinguish printed page numbers from catalogue t/b position suffixes.
    for row, original in zip(rows, remaining):
        assert row['song_no'] == original['song_no']
        assert row['catalogue_title'] == original['title']
        assert row['literal_heading'].removesuffix('.').replace('’', "'") == original['title']
        number = re.fullmatch(r'(\d+)([tb]?)', original['song_no'])
        assert number and row['printed_page'] == number.group(1)
        if number.group(2):
            assert row['page_region'] == {'t': 'top', 'b': 'bottom'}[number.group(2)]
        assert isinstance(row['pdf_leaf_1_based'], int) and row['pdf_leaf_1_based'] > 0
        assert row['source_pdf'] == data['source']['path']
        assert row['scan_sha256'] == data['source']['sha256']
        render = ROOT / row['render']
        assert render.name == f"leaf-{row['pdf_leaf_1_based']}.png"
        assert digest(render) == row['render_sha256']
        image_bytes = render.read_bytes()
        assert image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', image_bytes[16:24])
        assert row['render_dimensions_px'] == [width, height]
        x1, y1, x2, y2 = row['heading_bbox_px']
        assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
        assert row['status'] == 'source-page-identity-verified'
        assert row['review_method'] and row['observations']
        assert row['notation_present'] is True
        assert row['notation_imported'] is False
        assert row['exact_edition_notation_verified'] is False

    # Shared leaves are valid; shared source identity regions are not.
    assert len({(row['pdf_leaf_1_based'], row['page_region']) for row in rows}) == len(rows)
    summary = data['summary']
    assert summary['reviewed_records'] == summary['resolved_source_identities'] == len(rows)
    assert summary['distinct_reviewed_pdf_leaves'] == len({row['pdf_leaf_1_based'] for row in rows})
    assert summary['previous_combined_mapped'] == len(mapped)
    assert summary['previous_combined_unresolved'] == len(remaining)
    assert summary['combined_mapped'] == len(mapped) + len(rows)
    assert summary['combined_unresolved'] == len(remaining) - len(rows)
    assert summary['combined_mapped'] + summary['combined_unresolved'] == baseline['summary']['catalogue_records'] == summary['catalogue_records_unchanged']
    assert data['policy']['original_mapping_unchanged'] is True
    assert data['policy']['previous_supplements_unchanged'] is True
    assert data['policy']['notation_imported'] is False
    assert data['policy']['lyrics_or_notes_inferred'] is False
    assert '221' in data['policy']['catalogue_discrepancy'] and '222' in data['policy']['catalogue_discrepancy']
    print(json.dumps(dict(result='pass', reviewed_source_identities=len(rows), distinct_reviewed_pdf_leaves=summary['distinct_reviewed_pdf_leaves'], combined_mapped=summary['combined_mapped'], combined_unresolved=summary['combined_unresolved'], originals_unchanged=True, notation_imported=False, next_unresolved_record=remaining[len(rows)]['record_id'] if len(remaining) > len(rows) else None)))


if __name__ == '__main__':
    main()
