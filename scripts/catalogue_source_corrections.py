"""Narrow metadata overlay; run after publication or alone on a retained bundle.

Never rebuild unavailable musical inputs merely to correct catalogue metadata.
Stable IDs, paths, source files and score event streams are deliberately untouched.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_SALEM = 'kentucky 10 — New-Salem'
GLIMPSE = 'sacredharptunes a-glimpse-of-thee — A Glimpse of Thee L.M.'
OLD_LIMIT = 'Printed meter is L.M.D.; the catalogue label L.M. is preserved pending separate reconciliation.'
NEW_LIMIT = 'Printed meter L.M.D. is reflected in catalogue metadata; the stable record ID retains its historical L.M. suffix.'


def correct_song(song, evidence):
    """Apply only explicit record-scoped observations, preserving raw inputs."""
    if song['id'] not in (NEW_SALEM, GLIMPSE):
        return
    original = {key: copy.deepcopy(song.get(key)) for key in
                ('title', 'titlesByBook', 'rawFirstLine', 'textKey', 'textKeysByBook', 'textHub', 'metadata', 'metadataByBook')}
    if 'catalogueCorrection' not in song:
        song['catalogueCorrection'] = {
            'originalCatalogue': original,
            'evidenceUrl': '/catalogue-source-corrections.json',
            'witness': evidence[song['id']],
            'scope': 'catalogue metadata only; not note-level lyric underlay or score certification',
        }
    if song['id'] == NEW_SALEM:
        song['rawFirstLine'] = 'O thou in whose presence my soul takes delight,'
        song['textKey'] = 'o thou in whose presence my soul takes delight'
        song['textKeysByBook']['kentucky'] = song['textKey']
        song['textHub'] = 'text--o-thou-in-whose-presence-my-soul-takes-delight'
    else:
        song['title'] = 'A Glimpse of Thee L.M.D.'
        song['titlesByBook']['sacredharptunes'] = song['title']
        song.setdefault('metadataByBook', {}).setdefault('sacredharptunes', {})['meter'] = 'L.M.D.'
        song.setdefault('metadata', {})['meter'] = 'L.M.D.'
        replace_limit(song)


def replace_limit(value):
    if isinstance(value, dict):
        for child in value.values():
            replace_limit(child)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            if child == OLD_LIMIT:
                value[i] = NEW_LIMIT
            else:
                replace_limit(child)


def publish(root=ROOT):
    public = root / 'public'
    evidence = json.loads((public / 'catalogue-source-corrections.json').read_text())['records']
    paths = ['corpus.json', 'source-coverage.json', 'transcription-queue.json',
             'draft-scores/sacredharptunes-glimpse-v1.json']
    for name in paths:
        path = public / name
        before = path.read_text()
        data = json.loads(before)
        original = copy.deepcopy(data)
        if name == 'corpus.json':
            for song in data['songs']:
                correct_song(song, evidence)
        elif name in ('source-coverage.json', 'transcription-queue.json'):
            for record in data['records']:
                if record['songId'] == GLIMPSE:
                    replace_limit(record)
                    record['title'] = 'A Glimpse of Thee L.M.D.'
                    if name == 'transcription-queue.json':
                        record['meter'] = 'L.M.D.'
        else:
            replace_limit(data)
        if data != original:
            # Match each existing artifact's serialization, avoiding unrelated churn.
            indent = 2 if before.startswith('{\n') else None
            path.write_text(json.dumps(data, ensure_ascii=False, indent=indent,
                                       separators=None if indent else (',', ':')) + ('\n' if before.endswith('\n') else ''))


if __name__ == '__main__':
    publish()
