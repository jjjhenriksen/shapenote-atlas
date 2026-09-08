"""Reapply directly reviewed page identities without deleting catalogue history."""
import copy
import json
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
        # IDs, text, score mappings, raw evidence, and count summaries remain intact.
        for name in ('source-coverage', 'transcription-queue'):
            for record in result[name]['records']:
                if record.get('songId') == entry['songId'] and record.get('bookId') == 'trumpet':
                    record['title'] = entry['title']
                    record['sourceIdentityReview'] = copy.deepcopy(identity)
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
