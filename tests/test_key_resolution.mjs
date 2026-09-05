import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveKeyContext } from '../src/keyResolution.js';

const parseKey = (value) => /^(?:[A-G](?:#|b)?)(?: (?:major|minor))?$/.test(value || '') ? {} : null;
const keyEvidenceFor = (record, fallback = null) => record?.keyEvidence || fallback || { status: 'unknown', source: 'not recorded' };

test('reference witness does not borrow a differing selected-edition metadata key', () => {
  const result = resolveKeyContext(
    { keySignature: '', keyEvidence: { status: 'unknown', source: 'witness key unavailable' } },
    { keySignature: 'A minor', keyEvidence: { status: 'source-verified', source: 'selected-edition metadata' } },
    '',
    { parseKey, keyEvidenceFor, allowMetadataFallback: false },
  );
  assert.equal(result.value, '');
  assert.equal(result.evidence.status, 'unknown');
});

test('reference witness accepts its own key and then explicit manual entry', () => {
  const own = resolveKeyContext(
    { keySignature: 'Ab major', keyEvidence: { status: 'source-verified', source: 'witness MusicXML' } },
    { keySignature: 'A minor', keyEvidence: { status: 'source-verified', source: 'selected-edition metadata' } },
    '',
    { parseKey, keyEvidenceFor, allowMetadataFallback: false },
  );
  assert.equal(own.value, 'Ab major');
  const entered = resolveKeyContext(
    { keySignature: '', keyEvidence: { status: 'unknown', source: 'witness key unavailable' } },
    { keySignature: 'A minor', keyEvidence: { status: 'source-verified', source: 'selected-edition metadata' } },
    'G major',
    { parseKey, keyEvidenceFor, allowMetadataFallback: false },
  );
  assert.deepEqual(entered, { value: 'G major', evidence: { status: 'entered', source: 'user-entered source key' } });
});

test('exact score may still use edition metadata when its own key is absent', () => {
  const result = resolveKeyContext(
    { keySignature: '', keyEvidence: { status: 'unknown', source: 'score key unavailable' } },
    { keySignature: 'A minor', keyEvidence: { status: 'source-verified', source: 'edition metadata' } },
    '',
    { parseKey, keyEvidenceFor, allowMetadataFallback: true },
  );
  assert.equal(result.value, 'A minor');
  assert.equal(result.evidence.source, 'edition metadata');
});
