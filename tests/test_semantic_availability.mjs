import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { scoreSemanticSummary } from '../src/agent_11_score_semantics.js';

test('generated New Britain exposes source evidence while blocked playback stays linear', () => {
  const score = JSON.parse(readFileSync(new URL('../public/scores/c165d6455704c7c4595ab7c5.json', import.meta.url)));
  const summary = scoreSemanticSummary(score);
  assert.equal(summary.repeats, 'Source-encoded');
  assert.equal(summary.numberedEndings, 'Source-encoded');
  assert.equal(summary.playback, 'Linear source-order playback');
});

test('correction drafts and supported legacy string variants expose their evidence', () => {
  const score = JSON.parse(readFileSync(new URL('../public/draft-scores/sh2025-50t-devotion-v10.json', import.meta.url)));
  assert.equal(scoreSemanticSummary(score).lyrics, 'Source-encoded');
  assert.equal(scoreSemanticSummary({ semanticAvailability: { repeats: 'encoded' } }).repeats, 'Source-encoded');
  assert.equal(scoreSemanticSummary({ availability: { repeats: { status: 'encoded' } }, semanticContract: { availability: { repeats: { status: 'blocked' } } } }).repeats, 'Unavailable · source evidence incomplete');
  assert.equal(scoreSemanticSummary({}).repeats, 'Unavailable · not encoded in source');
});
