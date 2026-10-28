"""Read-only planning tests use synthetic bytes, never musical/source acceptance."""
import json
from pathlib import Path
import sys
import subprocess
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_transcription_acceptance_provenance as fixtures
import plan_transcription_publication as planner

class PublicationPlan(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AcceptanceProvenance()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.corpus = self.f.root / 'corpus.json'
        self.inventory = self.f.root / 'inventory.json'
        subject = self.f.declaration['subject']
        self.song = {'id': subject['recordId'], 'books': [subject['edition']]}
        self.corpus.write_text(json.dumps({'songs': [self.song]}))
        self.inventory.write_text(json.dumps({'schemaVersion': 1, 'records': []}))

    def plan(self):
        return planner.plan(self.f.path, self.f.bundle, self.f.pin, self.corpus, self.inventory)

    def test_partial_plan_is_pinned_nonmutating_and_never_authorizes(self):
        before = self.f.snapshot()
        result = self.plan()
        self.assertEqual(before, self.f.snapshot())
        self.assertFalse(result['proposedLabels']['completeWork'])
        self.assertEqual(result['mapping']['operation'], 'add')
        self.assertEqual(result['downloadableCandidates'][0]['sha256'], self.f.manifest['files']['candidate.musicxml'])
        for flag in ('acceptance', 'authorityVerified', 'evidenceVerified', 'sourceCertified', 'safeToPromote'):
            self.assertIs(result[flag], False)
        self.assertEqual(result['writes'], [])
        self.assertEqual(result['status'], 'blocked')

    def test_cli_is_read_only_and_returns_blocked_exit_status(self):
        before = self.f.snapshot()
        completed = subprocess.run([sys.executable, '-B', str(Path(planner.__file__)),
            str(self.f.path), str(self.f.bundle), '--expected-manifest-sha256', self.f.pin,
            '--corpus', str(self.corpus), '--inventory', str(self.inventory)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)['status'], 'blocked')
        self.assertEqual(self.f.snapshot(), before)

    def test_ambiguous_or_wrong_edition_mapping_has_no_proposal(self):
        for songs in ([self.song, self.song], [{**self.song, 'books': ['wrong']}], []):
            self.corpus.write_text(json.dumps({'songs': songs}))
            self.assertNotIn('mapping', self.plan())

    def test_version_collision_and_predecessor_are_reported(self):
        row = {key: self.f.declaration['subject'][key] for key in ('recordId', 'edition')}
        row.update(decisionId=self.f.declaration['decisionId'], manifestSha256='f' * 64)
        self.inventory.write_text(json.dumps({'schemaVersion': 1, 'records': [row]}))
        result = self.plan()
        self.assertEqual(result['predecessors']['versionCollisions'], [row])
        self.assertEqual(result['predecessors']['unpreserved'], [row])

    def test_changed_bundle_or_invalid_inventory_fails_closed(self):
        self.inventory.write_text('{"schemaVersion":1,"records":null}')
        self.assertNotIn('mapping', self.plan())
        (self.f.bundle / 'candidate.musicxml').write_bytes(b'changed')
        self.assertNotIn('mapping', self.plan())

    def test_rejected_declaration_never_proposes_permission(self):
        self.f.declaration['decision'] = 'reject'
        self.f.declaration['remainingBlockers']['admission'] = ['Rejected by source review']
        self.f.write_declaration()
        self.assertFalse(self.plan()['safeToPromote'])

if __name__ == '__main__': unittest.main()
