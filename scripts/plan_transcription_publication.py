#!/usr/bin/env python3
"""Read-only proposed publication diff; never grants admission or writes assets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import check_transcription_acceptance_provenance as provenance


def plan(declaration_path: Path, bundle: Path, pin: str, corpus_path: Path,
         inventory_path: Path) -> dict:
    check = provenance.check(declaration_path, bundle, pin)
    result = dict(schemaVersion=1, kind='shapenote-publication-plan', status='blocked',
                  acceptance=False, authorityVerified=False, evidenceVerified=False,
                  sourceCertified=False, safeToPromote=False, writes=[],
                  provenance=check, blockers=list(check['blockers']))
    if check['status'] != 'consistent':
        return result
    try:
        raw = declaration_path.read_bytes()
        if provenance.bundle_consumer.sha(raw) != check['declarationSha256']:
            raise ValueError('Declaration changed after provenance check')
        declaration = json.loads(raw, object_pairs_hook=provenance.declarations.unique_object)
        corpus_raw, inventory_raw = corpus_path.read_bytes(), inventory_path.read_bytes()
        corpus = json.loads(corpus_raw, object_pairs_hook=provenance.declarations.unique_object)
        inventory = json.loads(inventory_raw, object_pairs_hook=provenance.declarations.unique_object)
        if not isinstance(corpus, dict) or not isinstance(corpus.get('songs'), list):
            raise ValueError('Corpus requires songs array')
        if not isinstance(inventory, dict) or set(inventory) != {'schemaVersion', 'records'} or type(inventory['schemaVersion']) is not int or inventory['schemaVersion'] != 1 or not isinstance(inventory['records'], list):
            raise ValueError('Inventory requires schemaVersion 1 and records array')
        for row in inventory['records']:
            provenance.declarations.obj(row, ('recordId', 'edition', 'decisionId', 'manifestSha256'), 'inventory record')
            for key in ('recordId', 'edition', 'decisionId'):
                provenance.declarations.identifier(row[key], key)
            provenance.declarations.sha(row['manifestSha256'], 'manifestSha256')
        subject = declaration['subject']
        record_id, edition = subject['recordId'], subject['edition']
        matches = [song for song in corpus['songs'] if isinstance(song, dict) and song.get('id') == record_id]
        if len(matches) != 1 or edition not in matches[0].get('books', []):
            raise ValueError('Exact record/edition mapping missing or ambiguous')
        if not isinstance(matches[0].get('scoreByBook', {}), dict):
            raise ValueError('Existing score mapping must be an object')
        current = [row for row in inventory['records'] if row['recordId'] == record_id and row['edition'] == edition]
        declared = {(row['decisionId'], row['manifestSha256']) for row in declaration['predecessors']['records']}
        collisions = [row for row in inventory['records'] if row['decisionId'] == declaration['decisionId']]
        unpreserved = [row for row in current if (row['decisionId'], row['manifestSha256']) not in declared]
        result.update(inputPins={'corpusSha256': provenance.bundle_consumer.sha(corpus_raw),
                                 'inventorySha256': provenance.bundle_consumer.sha(inventory_raw)},
                      subject=subject, proposedVersion=declaration['decisionId'],
                      mapping={'recordId': record_id, 'edition': edition,
                               'operation': 'replace' if matches[0].get('scoreByBook', {}).get(edition) else 'add',
                               'existingScore': matches[0].get('scoreByBook', {}).get(edition),
                               'proposedManifestSha256': pin},
                      predecessors={'declared': declaration['predecessors'], 'current': current,
                                    'versionCollisions': collisions, 'unpreserved': unpreserved},
                      downloadableCandidates=[{'name': name, 'sha256': declaration['bundle']['payloadSha256'][name],
                                               'publishable': False} for name in ('candidate.musicxml', 'candidate.mxl')],
                      proposedLabels={'edition': edition, 'extent': subject['extent']['description'],
                                      'completeWork': subject['extent']['completeWork'],
                                      'status': 'Proposed candidate — not admitted or published'},
                      unsupportedSemantics=declaration['unsupportedSemantics'],
                      uncertainties=declaration['uncertainties'],
                      policyRestrictions=declaration['policyRestrictions'],
                      declaredGates=check['declaredDispositions'])
        for code, present in [('version-collision', collisions), ('unpreserved-predecessor', unpreserved)]:
            if present:
                result['blockers'].append({'code': code, 'detail': 'Resolve against the pinned inventory; no overwrite is planned.'})
        if declaration['decision'] != 'accept' or declaration['publication'] != 'permitted':
            result['blockers'].append({'code': 'declaration-does-not-permit-publication', 'detail': 'Retain declared rejection or publication blockers.'})
        result['blockers'].append({'code': 'independent-authority-and-evidence-required',
                                  'detail': 'Declaration consistency is not authorization, source review, rights clearance, or release QA. No public mutation is supported.'})
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        result['blockers'].append({'code': 'planning-input-invalid', 'detail': str(error)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('declaration', type=Path)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    args = parser.parse_args()
    result = plan(args.declaration, args.bundle, args.expected_manifest_sha256, args.corpus, args.inventory)
    print(json.dumps(result, sort_keys=True))
    return 2  # A plan is always blocked from execution, even when internally consistent.

if __name__ == '__main__':
    sys.exit(main())
