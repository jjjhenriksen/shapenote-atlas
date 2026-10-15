"""Reapply directly reviewed page identities without deleting catalogue history."""
import copy
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply(documents, manifest):
    result = copy.deepcopy(documents)
    songs = {song['id']: song for song in result['corpus']['songs']}
    for entry in manifest['records']:
        song = songs[entry['songId']]
        if song['books'] != ['trumpet'] or song['title'] not in (entry['originalTitle'], entry['title']):
            raise ValueError('Unexpected catalogue identity: ' + entry['songId'])
        identity = {**entry, 'sourceUrl': manifest['sourceUrl'] + '#page=' + str(entry['pdfLeaf']),
                    'sourceSha256': manifest['sourceSha256'], 'review': manifest['review']}
        song['title'] = entry['title']
        song.setdefault('titlesByBook', {})['trumpet'] = entry['title']
        song['sourceIdentityReview'] = identity
        song.setdefault('sourceCoverageByBook', {}).setdefault('trumpet', {})['sourceIdentityReview'] = copy.deepcopy(identity)
        song.setdefault('sourceCoverage', {})['sourceIdentityReview'] = copy.deepcopy(identity)
        if entry['contentKind'] == 'prose':
            if any(song.get(key, {}).get('trumpet') for key in
                   ('scoreByBook', 'referenceScoreByBook', 'draftScoreByBook')):
                raise ValueError('Prose record unexpectedly has notation: ' + entry['songId'])
            for coverage in (song['sourceCoverage'], song['sourceCoverageByBook']['trumpet']):
                coverage.update(contentKind='prose', status='non-notation', nextAction='preserve-prose-reference')
        # IDs, raw text, source evidence, and notation mappings remain intact.
        for name in ('source-coverage', 'transcription-queue'):
            for record in result[name]['records']:
                if record.get('songId') == entry['songId'] and record.get('bookId') == 'trumpet':
                    record['title'] = entry['title']
                    record['sourceIdentityReview'] = copy.deepcopy(identity)
                    if entry['contentKind'] == 'prose':
                        record.update(contentKind='prose', status='non-notation', nextAction='preserve-prose-reference')
    prose_ids = {entry['songId'] for entry in manifest['records'] if entry['contentKind'] == 'prose'}
    queue = result['transcription-queue']
    queue['records'] = [row for row in queue['records']
                        if not (row.get('bookId') == 'trumpet' and row.get('songId') in prose_ids)]
    if 'summary' in queue:
        queue['summary'] = {'total': len(queue['records']),
                            'byStatus': dict(Counter(row['status'] for row in queue['records'])),
                            'byBook': dict(Counter(row['bookId'] for row in queue['records']))}
        queue['policy'] = ('Every edition-specific notation record without an exact structured score is tracked here. '
                           'Reviewed prose stays in the catalogue and source-coverage ledger, not this notation queue. '
                           "Reference audio, scans, and other-edition scores never substitute for the edition's notation.")
    coverage = result['source-coverage']
    if 'summary' in coverage:
        coverage['summary']['proseRecords'] = sum(row.get('contentKind') == 'prose' for row in coverage['records'])
        coverage['summary']['notationRecords'] = len(coverage['records']) - coverage['summary']['proseRecords']
        coverage['summary']['sourceReferences'] = sum(row['status'] == 'source-reference' for row in coverage['records'])
    book_counts = result['corpus'].get('coverage', {}).get('byBook', {}).get('trumpet')
    if book_counts is not None:
        book_songs = [song for song in songs.values() if 'trumpet' in song.get('books', [])]
        prose_count = sum(song['id'] in prose_ids for song in book_songs)
        book_counts['proseRecords'] = prose_count
        book_counts['tuneRecords'] = len(book_songs) - prose_count
        book_counts['sourceReferenceRecords'] = sum(
            song.get('sourceCoverageByBook', {}).get('trumpet', {}).get('status') == 'source-reference'
            for song in book_songs)
    return result


def publish(root=ROOT, public=None):
    from review_publications import write_changed, json_bytes
    public = public or root / 'public'
    manifest = json.loads((root / 'scripts/trumpet-catalogue-review.json').read_text())
    documents = {name: json.loads((public / (name + '.json')).read_text())
                 for name in ('corpus', 'source-coverage', 'transcription-queue')}
    result = apply(documents, manifest)
    for name, document in result.items():
        write_changed(public / (name + '.json'), json_bytes(document))
    return len(manifest['records'])


if __name__ == '__main__':
    print('Applied Trumpet source identities:', publish())
