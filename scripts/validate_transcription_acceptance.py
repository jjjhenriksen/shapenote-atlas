#!/usr/bin/env python3
"""Validate proposed acceptance declarations only; never admit or publish a score."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

PAYLOADS = ('candidate.musicxml', 'candidate.mxl', 'report.json',
            'resolved-reading.json', 'comparison.json')
ASSESSMENTS = ('integrity', 'parsing', 'engraving', 'usefulPartial',
               'sourceFidelity', 'exactMapping', 'publicationRights',
               'xmlDownload', 'mxlDownload', 'uiLabels', 'writtenPlayback',
               'encodedRepeatPlayback', 'hostedReleaseQa', 'nativeReleaseQa')
EVIDENCE_KINDS = set(ASSESSMENTS) | {'authorization', 'humanImage', 'predecessor'}
ADMISSION_GATES = ('integrity', 'parsing', 'sourceFidelity', 'exactMapping')
PUBLICATION_GATES = ADMISSION_GATES + ('engraving', 'publicationRights',
                    'xmlDownload', 'mxlDownload', 'uiLabels', 'writtenPlayback',
                    'encodedRepeatPlayback')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def obj(value: Any, keys: tuple[str, ...], path: str) -> dict:
    require(type(value) is dict, f'{path}: expected object')
    require(set(value) == set(keys), f'{path}: expected exactly {", ".join(keys)}')
    return value


def text(value: Any, path: str) -> str:
    require(type(value) is str and bool(value.strip()), f'{path}: expected nonempty string')
    return value


def choice(value: Any, choices: tuple[str, ...], path: str) -> str:
    require(type(value) is str and value in choices, f'{path}: expected one of {choices}')
    return value


def strings(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    require(type(value) is list, f'{path}: expected array')
    for item in value:
        text(item, path)
    require(len(set(value)) == len(value), f'{path}: duplicate values')
    require(not nonempty or bool(value), f'{path}: must not be empty')
    return value


def sha(value: Any, path: str, size: int = 64) -> str:
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{' + str(size) + '}', value)
            is not None, f'{path}: expected lowercase {size}-digit hex pin')
    return value


def timestamp(value: Any, path: str) -> None:
    text(value, path)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError(f'{path}: expected ISO timestamp with timezone') from error
    require(parsed.tzinfo is not None and 'T' in value,
            f'{path}: expected ISO timestamp with timezone')


def extent(value: Any, path: str) -> None:
    obj(value, ('description', 'sourcePages', 'partIds', 'measureIds', 'completeWork'), path)
    text(value['description'], path + '.description')
    for key in ('sourcePages', 'partIds', 'measureIds'):
        strings(value[key], path + '.' + key, nonempty=True)
        require('*' not in value[key], f'{path}.{key}: wildcard scope is forbidden')
    require(type(value['completeWork']) is bool, f'{path}.completeWork: expected boolean')


def validate(decision: Any) -> dict:
    """Check shape, pin syntax, references and contradictions, without opening evidence."""
    obj(decision, ('schemaVersion', 'kind', 'contractStatus', 'decisionId', 'recordedAt',
                  'subject', 'bundle', 'privateEvidenceLocator', 'evidence', 'owner',
                  'decision', 'decisionReasons', 'humanImageReview', 'assessments',
                  'unsupportedSemantics', 'uncertainties', 'policyRestrictions',
                  'remainingBlockers', 'publication', 'predecessors', 'residualAtlasIssues'), '$')
    require(type(decision['schemaVersion']) is int and decision['schemaVersion'] == 1,
            '$.schemaVersion: only proposed version 1 is supported')
    require(decision['kind'] == 'shapenote-transcription-acceptance-decision', '$.kind: unsupported kind')
    require(decision['contractStatus'] == 'proposed', '$.contractStatus: must remain proposed')
    text(decision['decisionId'], '$.decisionId')
    timestamp(decision['recordedAt'], '$.recordedAt')
    subject = obj(decision['subject'], ('recordId', 'edition', 'extent'), '$.subject')
    for key in ('recordId', 'edition'):
        text(subject[key], '$.subject.' + key)
        require(subject[key] != '*', '$.subject: wildcard identity is forbidden')
    extent(subject['extent'], '$.subject.extent')

    bundle = obj(decision['bundle'], ('schemaVersion', 'manifestSha256', 'sourceSha256',
                 'producer', 'actualWriterSha256', 'payloadSha256', 'researchFlags'), '$.bundle')
    require(type(bundle['schemaVersion']) is int and bundle['schemaVersion'] == 1,
            '$.bundle.schemaVersion: only bundle v1 is supported')
    for key in ('manifestSha256', 'sourceSha256', 'actualWriterSha256'):
        sha(bundle[key], '$.bundle.' + key)
    producer = obj(bundle['producer'], ('repository', 'revision', 'dirty', 'exporterSha256'),
                   '$.bundle.producer')
    text(producer['repository'], '$.bundle.producer.repository')
    sha(producer['revision'], '$.bundle.producer.revision', 40)
    sha(producer['exporterSha256'], '$.bundle.producer.exporterSha256')
    require(type(producer['dirty']) is bool, '$.bundle.producer.dirty: expected boolean')
    payloads = obj(bundle['payloadSha256'], PAYLOADS, '$.bundle.payloadSha256')
    for key, pin in payloads.items():
        sha(pin, '$.bundle.payloadSha256.' + key)
    flags = obj(bundle['researchFlags'], ('sourceCertified', 'safeToPromote'), '$.bundle.researchFlags')
    require(all(value is False for value in flags.values()), '$.bundle.researchFlags: must remain false')
    locator = text(decision['privateEvidenceLocator'], '$.privateEvidenceLocator')
    require(locator.startswith('private://') and len(locator) > len('private://'),
            '$.privateEvidenceLocator: expected opaque private:// locator')

    require(type(decision['evidence']) is list, '$.evidence: expected array')
    evidence = {}
    for item in decision['evidence']:
        obj(item, ('id', 'kind', 'locator', 'sha256', 'subjectSha256'), '$.evidence[]')
        key = text(item['id'], '$.evidence[].id')
        require(key not in evidence, '$.evidence: duplicate id')
        choice(item['kind'], tuple(sorted(EVIDENCE_KINDS)), '$.evidence[].kind')
        text(item['locator'], '$.evidence[].locator')
        sha(item['sha256'], '$.evidence[].sha256')
        sha(item['subjectSha256'], '$.evidence[].subjectSha256')
        evidence[key] = item

    def refs(value: Any, path: str, kind: str, pin: str, required: bool = True) -> None:
        for key in strings(value, path, nonempty=required):
            require(key in evidence, f'{path}: unknown evidence id {key}')
            require(evidence[key]['kind'] == kind, f'{path}: evidence kind must be {kind}')
            require(evidence[key]['subjectSha256'] == pin, f'{path}: evidence subject pin mismatch')

    owner = obj(decision['owner'], ('name', 'authorizationEvidence'), '$.owner')
    text(owner['name'], '$.owner.name')
    refs(owner['authorizationEvidence'], '$.owner.authorizationEvidence', 'authorization', bundle['manifestSha256'])
    outcome = choice(decision['decision'], ('accept', 'reject', 'blocked'), '$.decision')
    strings(decision['decisionReasons'], '$.decisionReasons', nonempty=True)
    for key in ('unsupportedSemantics', 'uncertainties', 'policyRestrictions'):
        strings(decision[key], '$.' + key)
    blockers = obj(decision['remainingBlockers'], ('admission', 'publication'), '$.remainingBlockers')
    for key in blockers:
        strings(blockers[key], '$.remainingBlockers.' + key)
    publication = choice(decision['publication'], ('permitted', 'blocked', 'not-requested'), '$.publication')

    human = obj(decision['humanImageReview'], ('disposition', 'reviewer', 'reviewedAt',
                'sourceSha256', 'extent', 'evidence', 'note'), '$.humanImageReview')
    disposition = choice(human['disposition'], ('matched', 'mismatch', 'unreviewed'),
                         '$.humanImageReview.disposition')
    require(human['sourceSha256'] == bundle['sourceSha256'], '$.humanImageReview: source pin mismatch')
    extent(human['extent'], '$.humanImageReview.extent')
    require(human['extent'] == subject['extent'], '$.humanImageReview: extent mismatch')
    text(human['note'], '$.humanImageReview.note')
    refs(human['evidence'], '$.humanImageReview.evidence', 'humanImage', bundle['sourceSha256'],
         required=disposition != 'unreviewed')
    if disposition == 'unreviewed':
        require(human['reviewer'] is None and human['reviewedAt'] is None,
                '$.humanImageReview: unreviewed must not name a completed review')
    else:
        text(human['reviewer'], '$.humanImageReview.reviewer')
        timestamp(human['reviewedAt'], '$.humanImageReview.reviewedAt')

    assessments = obj(decision['assessments'], ASSESSMENTS, '$.assessments')
    for key, assessment in assessments.items():
        path = '$.assessments.' + key
        obj(assessment, ('disposition', 'evidence', 'note'), path)
        result = choice(assessment['disposition'], ('passed', 'failed', 'unknown', 'not-applicable'), path)
        text(assessment['note'], path + '.note')
        pin = bundle['sourceSha256'] if key == 'sourceFidelity' else bundle['manifestSha256']
        if key in ('xmlDownload', 'mxlDownload'):
            pin = payloads['candidate.musicxml' if key == 'xmlDownload' else 'candidate.mxl']
        refs(assessment['evidence'], path + '.evidence', key, pin, required=result in ('passed', 'failed'))
    fidelity = assessments['sourceFidelity']['disposition']
    require(fidelity != 'passed' or disposition == 'matched',
            '$.assessments.sourceFidelity: passing requires matched human image review')
    require(disposition != 'mismatch' or fidelity == 'failed',
            '$.assessments.sourceFidelity: source mismatch must remain failed')

    if outcome == 'accept':
        require(all(assessments[key]['disposition'] == 'passed' for key in ADMISSION_GATES),
                '$.decision: accept requires all admission gates passed')
        require(not blockers['admission'] and not decision['unsupportedSemantics'] and
                not decision['uncertainties'] and not decision['policyRestrictions'],
                '$.decision: accept contradicts unresolved admission restrictions')
    elif outcome == 'blocked':
        require(bool(blockers['admission']), '$.decision: blocked requires admission blockers')
    if publication == 'permitted':
        require(outcome == 'accept', '$.publication: permission requires accepted admission declaration')
        require(all(assessments[key]['disposition'] == 'passed' for key in PUBLICATION_GATES),
                '$.publication: required publication gates have not passed')
        require(all(assessments[key]['disposition'] in ('passed', 'not-applicable')
                    for key in ('hostedReleaseQa', 'nativeReleaseQa')),
                '$.publication: hosted/native release QA must be separately resolved')
        require(not blockers['publication'], '$.publication: permission contradicts publication blockers')
    elif publication == 'blocked':
        require(bool(blockers['publication']), '$.publication: blocked requires publication blockers')

    predecessors = obj(decision['predecessors'], ('disposition', 'records'), '$.predecessors')
    choice(predecessors['disposition'], ('none', 'preserved'), '$.predecessors.disposition')
    require(type(predecessors['records']) is list, '$.predecessors.records: expected array')
    require(bool(predecessors['records']) == (predecessors['disposition'] == 'preserved'),
            '$.predecessors: records must agree with preservation disposition')
    predecessor_ids = set()
    for previous in predecessors['records']:
        obj(previous, ('decisionId', 'manifestSha256', 'evidence'), '$.predecessors.records[]')
        previous_id = text(previous['decisionId'], '$.predecessors.records[].decisionId')
        require(previous_id != decision['decisionId'] and previous_id not in predecessor_ids,
                '$.predecessors: self-reference or duplicate decision id')
        predecessor_ids.add(previous_id)
        sha(previous['manifestSha256'], '$.predecessors.records[].manifestSha256')
        refs(previous['evidence'], '$.predecessors.records[].evidence', 'predecessor', previous['manifestSha256'])
    for issue in strings(decision['residualAtlasIssues'], '$.residualAtlasIssues'):
        require(re.fullmatch(r'https://github\.com/jjjhenriksen/shapenote-atlas/issues/[1-9][0-9]*', issue)
                is not None, '$.residualAtlasIssues: expected Atlas issue URL')
    return {'schemaVersion': 1, 'status': 'valid-declaration', 'decision': outcome,
            'acceptance': False, 'authorityVerified': False, 'evidenceVerified': False,
            'sourceCertified': False, 'safeToPromote': False}


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    value = {}
    for key, item in pairs:
        require(key not in value, f'duplicate JSON key: {key}')
        value[key] = item
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decision', type=Path, help='private proposed decision JSON (read only)')
    args = parser.parse_args(argv)
    try:
        decision = json.loads(args.decision.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
        result = validate(decision)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        print(json.dumps({'schemaVersion': 1, 'status': 'invalid-declaration',
                          'acceptance': False, 'error': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
