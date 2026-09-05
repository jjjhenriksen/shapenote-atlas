import test from 'node:test';
import assert from 'node:assert/strict';
import { presentSourceHealthRecord, summarizeSourceHealth } from '../src/sourceHealthPresentation.js';

test('cached unreachable evidence stays separate from its network state and date', () => {
 const result = presentSourceHealthRecord({ status: 'cached', networkStatus: 'unreachable', checkedAt: '2026-09-05T03:00:00Z', retentionStatus: 'missing-retention' });
 assert.equal(result.evidenceState, 'cached');
 assert.equal(result.networkState, 'unreachable');
 assert.equal(result.networkCheckedAt, null);
 assert.match(result.text, /Cached check/);
 assert.match(result.text, /Unreachable/);
 assert.match(result.text, /date unavailable/);
 assert.equal(result.sourceAuthority, 'not-established');
});

test('cached network errors use networkCheckedAt, never report checkedAt as a network check', () => {
 const result = presentSourceHealthRecord({ status: 'cached', networkStatus: 'network-error', checkedAt: '2026-09-05T04:00:00Z', networkCheckedAt: '2026-09-05T02:40:00Z', retentionStatus: 'retention-unavailable' });
 assert.equal(result.evidenceState, 'cached');
 assert.equal(result.networkState, 'network-error');
 assert.equal(result.networkCheckedDate, '2026-09-05');
 assert.match(result.text, /Network error/);
});

test('budget-only records are not presented as current or cached', () => {
 const result = summarizeSourceHealth([{ status: 'not-checked-budget', retentionStatus: 'missing-retention', checkedAt: '2026-09-05T04:00:00Z' }]);
 assert.deepEqual(result.evidenceCounts, { current: 0, cached: 0, offline: 0, budget: 1, unknown: 0 });
 assert.equal(result.networkCounts['not-checked-budget'], 1);
 assert.equal(result.latestNetworkCheckedAt, null);
 assert.match(result.text, /1 budget-excluded/);
});

test('empty or unknown records do not assert freshness', () => {
 const result = presentSourceHealthRecord({});
 assert.equal(result.evidenceState, 'unknown');
 assert.equal(result.networkState, 'unknown');
 assert.equal(result.networkCheckedAt, null);
 assert.match(result.text, /Evidence state unavailable/);
 assert.match(result.text, /date unavailable/);
});

test('summary does not hide mixed drift behind retained exact evidence', () => {
 const result = summarizeSourceHealth([
  { status: 'cached', networkStatus: 'reachable', retentionStatus: 'retained-exact', networkCheckedAt: '2026-09-05T02:00:00Z' },
  { status: 'cached', networkStatus: 'reachable', retentionStatus: 'local-drift', networkCheckedAt: '2026-09-05T03:00:00Z' },
 ]);
 assert.equal(result.retentionState, 'local-drift');
 assert.match(result.retentionLabel, /drift present/);
 assert.equal(result.retentionCounts['retained-exact'], 1);
 assert.equal(result.retentionCounts['local-drift'], 1);
 assert.equal(result.sourceAuthority, 'not-established');
});

test('summary does not treat exact plus unknown retention as universal exactness', () => {
 const result = summarizeSourceHealth([
  { status: 'cached', networkStatus: 'reachable', retentionStatus: 'retained-exact' },
  { status: 'cached', networkStatus: 'reachable' },
 ]);
 assert.equal(result.retentionState, 'mixed-retention');
 assert.match(result.retentionLabel, /unavailable/);
 assert.equal(result.retentionCounts['unknown-retention'], 1);
});

test('summary separates current and cached evidence from reachable and unreachable counts', () => {
 const result = summarizeSourceHealth([
  { status: 'reachable', retentionStatus: 'missing-retention', networkCheckedAt: '2026-09-05T01:00:00Z' },
  { status: 'cached', networkStatus: 'reachable', retentionStatus: 'retained-exact', networkCheckedAt: '2026-09-05T00:00:00Z' },
  { status: 'cached', networkStatus: 'unreachable', retentionStatus: 'missing-retention' },
 ]);
 assert.deepEqual(result.evidenceCounts, { current: 1, cached: 2, offline: 0, budget: 0, unknown: 0 });
 assert.equal(result.networkCounts.reachable, 2);
 assert.equal(result.networkCounts.unreachable, 1);
 assert.match(result.text, /1 current · 2 cached/);
 assert.match(result.text, /2 reachable · 0 redirected · 1 unreachable/);
});
