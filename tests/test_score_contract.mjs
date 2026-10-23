import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateScore } from '../src/scoreContract.js';

const sourceUrl = 'https://example.invalid/synthetic-score';
const valid = () => ({ sourceUrl, parts: [{ name: 'Tenor', events: [{ onset: 0, beats: 1, step: 'C', octave: 4 }] }] });
for (const [name, make] of Object.entries({
  null: () => null, array: () => [], missingParts: () => ({ sourceUrl }), objectParts: () => ({ sourceUrl, parts: {} }),
  nullPart: () => ({ sourceUrl, parts: [null] }), missingName: () => ({ sourceUrl, parts: [{ events: [] }] }),
  objectName: () => ({ sourceUrl, parts: [{ name: {}, events: [] }] }),
  missingEvents: () => ({ sourceUrl, parts: [{ name: 'Tenor' }] }),
  objectEvents: () => ({ sourceUrl, parts: [{ name: 'Tenor', events: {} }] }),
  nullEvent: () => ({ sourceUrl, parts: [{ name: 'Tenor', events: [null] }] }),
  arrayEvent: () => ({ sourceUrl, parts: [{ name: 'Tenor', events: [[]] }] }),
  missingSource: () => ({ parts: [] }), wrongSource: () => ({ ...valid(), sourceUrl: 'https://example.invalid/other' }),
  objectMeter: () => ({ ...valid(), timeSignature: {} }),
  stringRepeatSequence: () => ({ ...valid(), playback: { status: 'encoded', safeToApply: true, measureSequence: '12' } }),
  nestedRepeatSequence: () => ({ ...valid(), semanticContract: { playback: { measureSequence: {} } } }),
})) test(`rejects malformed full score ${name}`, () => assert.throws(() => validateScore(make(), sourceUrl), /Incompatible full score/));

test('empty and rest-only scores remain valid without optional metadata', () => {
  for (const parts of [[], [{ name: 'Tenor', events: [] }], [{ name: 'Tenor', events: [{ rest: true, onset: 0, beats: 1 }] }]]) {
    const score = { sourceUrl, parts }; assert.equal(validateScore(score, sourceUrl), score);
  }
});

test('structural validation neither changes data nor adjudicates musical timing', () => {
  const score = valid(); score.parts[0].events[0].beats = -1;
  score.playbackValidation = { status: 'quarantined', safeToApply: false };
  const before = structuredClone(score);
  assert.equal(validateScore(score, sourceUrl), score); assert.deepEqual(score, before);
  assert.throws(() => validateScore(score, ''), /requested witness/);
});

for (const field of ['lyrics', 'barlines', 'measureSemantics']) {
  test(`rejects malformed optional part ${field}`, () => {
    const score = valid(); score.parts[0][field] = [null];
    assert.throws(() => validateScore(score, sourceUrl), /Incompatible full score/);
  });
}
for (const field of ['lyrics', 'editorialMarkings']) {
  test(`rejects malformed optional event ${field}`, () => {
    const score = valid(); score.parts[0].events[0][field] = {};
    assert.throws(() => validateScore(score, sourceUrl), /Incompatible full score/);
  });
}

test('all referenced committed full scores satisfy the boundary without source mutation', () => {
  const corpus = JSON.parse(readFileSync(new URL('../public/corpus.json', import.meta.url)));
  let checked = 0;
  for (const song of corpus.songs) for (const field of ['scoreByBook', 'referenceScoreByBook', 'draftScoreByBook']) {
    for (const preview of Object.values(song[field] || {})) {
      if (!preview?.scoreRef) continue;
      const score = JSON.parse(readFileSync(new URL(`../public${preview.scoreRef}`, import.meta.url)));
      const before = JSON.stringify(score);
      assert.equal(validateScore(score, preview.sourceUrl), score);
      assert.equal(JSON.stringify(score), before); checked++;
    }
  }
  assert.ok(checked > 1000);
});
