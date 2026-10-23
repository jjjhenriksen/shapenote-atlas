"""Synthetic declaration tests, never real source/rights/admission evidence."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_transcription_acceptance as validator

FIXTURE = ROOT / 'tests/fixtures/transcription-acceptance/synthetic-accepted-declaration.json'


class AcceptanceDeclarations(unittest.TestCase):
    def setUp(self):
        self.decision = json.loads(FIXTURE.read_text())

    def reject(self, decision=None):
        with self.assertRaises(ValueError):
            validator.validate(self.decision if decision is None else decision)

    def test_accepted_schema_is_not_acceptance_or_publication(self):
        result = validator.validate(self.decision)
        self.assertEqual(result['status'], 'valid-declaration')
        for key in ('acceptance', 'authorityVerified', 'evidenceVerified',
                    'sourceCertified', 'safeToPromote'):
            self.assertIs(result[key], False)
        self.assertEqual(self.decision['publication'], 'blocked')
        self.assertEqual(self.decision['assessments']['publicationRights']['disposition'], 'unknown')

    def test_blocked_and_rejected_source_mismatch_declarations_are_valid(self):
        self.decision['decision'] = 'blocked'
        self.decision['remainingBlockers']['admission'] = ['Human image review found a source mismatch.']
        self.decision['humanImageReview']['disposition'] = 'mismatch'
        self.decision['assessments']['sourceFidelity']['disposition'] = 'failed'
        validator.validate(self.decision)
        self.decision['decision'] = 'reject'
        validator.validate(self.decision)

    def test_required_fields_unknown_fields_types_and_versions_fail_closed(self):
        for key in self.decision:
            changed = deepcopy(self.decision)
            del changed[key]
            with self.subTest(missing=key):
                self.reject(changed)
        for path, value in ((['extra'], True), (['schemaVersion'], True),
                            (['schemaVersion'], 2), (['contractStatus'], 'approved'),
                            (['bundle','schemaVersion'], 2),
                            (['bundle','producer','dirty'], 0),
                            (['subject','extent','completeWork'], 'false'),
                            (['unsupportedSemantics'], 'none'),
                            (['recordedAt'], '2026-10-22'),
                            (['evidence'], {})):
            changed = deepcopy(self.decision)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path):
                self.reject(changed)

    def test_all_provenance_pins_and_candidate_flags_are_required(self):
        paths = [('manifestSha256',), ('sourceSha256',), ('actualWriterSha256',),
                 ('producer','revision'), ('producer','exporterSha256',)]
        paths += [('payloadSha256', key) for key in validator.PAYLOADS]
        for path in paths:
            changed = deepcopy(self.decision)
            target = changed['bundle']
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = 'short'
            with self.subTest(path=path):
                self.reject(changed)
        for flag in ('sourceCertified', 'safeToPromote'):
            changed = deepcopy(self.decision)
            changed['bundle']['researchFlags'][flag] = True
            self.reject(changed)

    def test_accept_cannot_hide_human_mismatch_unknown_gates_or_restrictions(self):
        for gate in validator.ADMISSION_GATES:
            changed = deepcopy(self.decision)
            changed['assessments'][gate]['disposition'] = 'unknown'
            self.reject(changed)
        for key in ('unsupportedSemantics', 'uncertainties', 'policyRestrictions'):
            changed = deepcopy(self.decision)
            changed[key] = ['Unresolved within declared extent.']
            self.reject(changed)
        self.decision['remainingBlockers']['admission'] = ['Pending source review.']
        self.reject()
        self.decision['decision'] = 'blocked'
        validator.validate(self.decision)
        self.decision['remainingBlockers']['admission'] = []
        self.reject()

    def test_human_review_must_match_source_extent_and_named_review(self):
        for key, value in (('sourceSha256', 'f'*64), ('reviewer', None),
                           ('reviewedAt', None), ('evidence', []),
                           ('disposition', 'mismatch')):
            changed = deepcopy(self.decision)
            changed['humanImageReview'][key] = value
            self.reject(changed)
        self.decision['humanImageReview']['extent']['measureIds'] = ['2']
        self.reject()

    def test_unknown_duplicate_wrong_kind_and_wrong_subject_evidence_are_rejected(self):
        changed = deepcopy(self.decision)
        changed['assessments']['integrity']['evidence'] = ['missing']
        self.reject(changed)
        changed = deepcopy(self.decision)
        changed['evidence'].append(deepcopy(changed['evidence'][0]))
        self.reject(changed)
        for key, value in (('kind','parsing'), ('subjectSha256','f'*64), ('sha256','bad')):
            changed = deepcopy(self.decision)
            changed['evidence'][0][key] = value
            self.reject(changed)

    def test_publication_has_separate_rights_download_and_release_gates(self):
        self.decision['publication'] = 'permitted'
        self.decision['remainingBlockers']['publication'] = []
        self.reject()
        for key in validator.PUBLICATION_GATES + ('hostedReleaseQa','nativeReleaseQa'):
            assessment = self.decision['assessments'][key]
            assessment['disposition'] = 'passed'
            pin = self.decision['bundle']['sourceSha256'] if key == 'sourceFidelity' else self.decision['bundle']['manifestSha256']
            if key in ('xmlDownload','mxlDownload'):
                payload = 'candidate.musicxml' if key == 'xmlDownload' else 'candidate.mxl'
                pin = self.decision['bundle']['payloadSha256'][payload]
            if not assessment['evidence']:
                assessment['evidence'] = [key]
                self.decision['evidence'].append({'id':key, 'kind':key,
                    'locator':'private://synthetic/' + key, 'sha256':'f'*64, 'subjectSha256':pin})
        validator.validate(self.decision)
        for gate in validator.PUBLICATION_GATES + ('hostedReleaseQa','nativeReleaseQa'):
            changed = deepcopy(self.decision)
            changed['assessments'][gate]['disposition'] = 'unknown'
            self.reject(changed)
        changed = deepcopy(self.decision)
        next(item for item in changed['evidence'] if item['kind'] == 'xmlDownload')['subjectSha256'] = '0'*64
        self.reject(changed)

    def test_predecessor_requires_retained_evidence_and_no_self_reference(self):
        self.decision['predecessors'] = {'disposition':'preserved','records':[
            {'decisionId':'synthetic-previous','manifestSha256':'b'*64,'evidence':['previous']}]}
        self.reject()
        self.decision['evidence'].append({'id':'previous','kind':'predecessor',
            'locator':'private://synthetic/previous','sha256':'c'*64,'subjectSha256':'b'*64})
        validator.validate(self.decision)
        self.decision['predecessors']['records'][0]['decisionId'] = self.decision['decisionId']
        self.reject()

    def test_identity_and_extent_tokens_are_explicit_without_wildcards_or_padding(self):
        invalid_tokens = ('*', '* ', ' *', 'prefix*suffix', 'sh2025/*', 'page-*', 'S*', '1*',
                          ' synthetic ', 'synthetic\nrecord', 'synthetic\trecord', 'synthetic\x00record')
        for field in ('recordId', 'edition', 'sourcePages', 'partIds', 'measureIds'):
            for token in invalid_tokens:
                changed = deepcopy(self.decision)
                if field in ('recordId', 'edition'):
                    changed['subject'][field] = token
                else:
                    changed['subject']['extent'][field] = [token]
                    changed['humanImageReview']['extent'][field] = [token]
                with self.subTest(field=field, token=repr(token)):
                    self.reject(changed)

    def test_explicit_identifiers_and_free_prose_keep_legitimate_punctuation(self):
        self.decision['subject']['recordId'] = 'sh2025/50t'
        self.decision['subject']['edition'] = 'Sacred Harp 2025'
        for field, tokens in (('sourcePages', ['page-1', 'page-2']),
                              ('partIds', ['S.1', 'A-1', 'T/1', 'B_1']),
                              ('measureIds', ['0-pickup', '1a', '2'])):
            self.decision['subject']['extent'][field] = tokens
            self.decision['humanImageReview']['extent'][field] = tokens
        self.decision['subject']['extent']['description'] = 'A literal * in explanatory prose.'
        self.decision['humanImageReview']['extent']['description'] = self.decision['subject']['extent']['description']
        self.decision['decisionReasons'] = ['Exact scope; note * as ordinary prose punctuation.']
        self.decision['humanImageReview']['note'] = 'Reviewed * as a printed annotation.'
        validator.validate(self.decision)

    def test_malformed_timezone_components_and_nonprofile_timestamps_are_rejected(self):
        invalid_times = ('2026-10-22T12:00:00+00:99', '2026-10-22T12:00:00+01:60',
                         '2026-10-22T12:00:00+00:00:99', '2026-10-22T12:00:00+24:00',
                         '2026-10-22T12:00:00+0000', '2026-10-22T12:00:00',
                         '2026-10-22T12:00:00Z ', '2026-10-22T24:00:00Z',
                         '2026-10-22T12:60:00Z', '2026-10-22T12:00:60Z',
                         '2026-02-30T12:00:00Z')
        for field in ('recordedAt', 'reviewedAt'):
            for value in invalid_times:
                changed = deepcopy(self.decision)
                target = changed if field == 'recordedAt' else changed['humanImageReview']
                target[field] = value
                with self.subTest(field=field, value=value):
                    self.reject(changed)

    def test_supported_timestamp_precision_and_timezone_forms_remain_valid(self):
        valid_times = ('2026-10-22T12:00Z', '2026-10-22T12:00:00Z',
                       '2026-10-22T12:00:00.123456789Z', '2026-10-22T12:00+01:30',
                       '2026-10-22T12:00:00.1-07:00', '2024-02-29T12:00:00+00:00')
        for field in ('recordedAt', 'reviewedAt'):
            for value in valid_times:
                changed = deepcopy(self.decision)
                target = changed if field == 'recordedAt' else changed['humanImageReview']
                target[field] = value
                with self.subTest(field=field, value=value):
                    validator.validate(changed)

    def test_cli_reads_only_and_reports_invalid_json_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'decision.json'
            original = FIXTURE.read_bytes()
            path.write_bytes(original)
            command = [sys.executable, str(ROOT / 'scripts/validate_transcription_acceptance.py'), str(path)]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'valid-declaration')
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.iterdir()), [path])
            for content in ('{', '{"decision":1,"decision":2}', '\xff'):
                path.write_text(content)
                result = subprocess.run(command, cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)['status'], 'invalid-declaration')
            path.unlink()
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
