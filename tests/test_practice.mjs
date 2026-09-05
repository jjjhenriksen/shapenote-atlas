import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPracticeSchedule, guardedAudioAction, resolvePlaybackQuarantine, scheduleWithCleanup, sessionIsCurrent, shouldCompleteSession } from '../src/practice.js';

const parts = [{ name: 'Tenor', events: [{ measure: 1, onset: 0, beats: 1 }, { measure: 2, onset: 1, beats: 1 }] }];

test('production quarantine resolver checks preview and full score independently', () => {
 assert.equal(resolvePlaybackQuarantine({ playbackValidation: { status: 'quarantined', reason: 'preview' } }, null).reason, 'preview');
 assert.equal(resolvePlaybackQuarantine({}, { playbackValidation: { safeToApply: false, reason: 'full' } }).reason, 'full');
 assert.equal(resolvePlaybackQuarantine({ playbackValidation: { safeToApply: true } }, { playbackValidation: { status: 'quarantined', reason: 'disagree' } }).reason, 'disagree');
 assert.equal(resolvePlaybackQuarantine({ playbackValidation: { safeToApply: true } }, { playbackValidation: { status: 'valid', safeToApply: true } }).quarantined, false);
});

test('audio-time completion survives a pause beyond the original wall-clock deadline', () => {
 const session = { startedAt: 10, duration: 2, owner: null, cancelled: false }; session.owner = session;
 assert.equal(shouldCompleteSession(11, session), false);
 assert.equal(shouldCompleteSession(11, session), false);
 assert.equal(shouldCompleteSession(12, session), true);
});

test('encoded repeats are expanded before two practice loops', () => {
 const result = buildPracticeSchedule(parts, { status: 'encoded', safeToApply: true, measureSequence: [1, 2, 1], measureStarts: { 1: 0, 2: 1 }, measureDurations: { 1: 1, 2: 1 } }, 2);
 assert.equal(result.duration, 6);
 assert.deepEqual(result.events.map((event) => `${event.id || event.measure}@${event.scheduledOnset}`), ['1@0', '2@1', '1@2', '1@3', '2@4', '1@5']);
});

test('pending resume cancellation rejects stale session state', () => {
 const session = { cancelled: false }; const replacement = { cancelled: false };
 assert.equal(sessionIsCurrent(session, session), true);
 session.cancelled = true;
 assert.equal(sessionIsCurrent(session, session), false);
 assert.equal(sessionIsCurrent(replacement, session), false);
});

test('mid-schedule failure stops all nodes already created', () => {
 const stopped = []; let calls = 0;
 assert.throws(() => scheduleWithCleanup([1, 2, 3], () => { calls += 1; if (calls === 3) throw new Error('fake scheduling failure'); const node = { stop: () => stopped.push(calls) }; return node; }));
 assert.deepEqual(stopped, [3, 3]);
});

test('post-allocation start failure cleans every production-registered node', () => {
 const stopped = []; const allocated = [];
 assert.throws(() => scheduleWithCleanup(['A', 'B', 'C'], (id) => { const node = { id, stop: () => stopped.push(id) }; allocated.push(id); return node; }, (node) => { if (node.id === 'B') throw new Error('start failed after allocation'); }));
 assert.deepEqual(allocated, ['A', 'B']);
 assert.deepEqual(stopped, ['A', 'B']);
});

test('practice settings are bounded and schedule cancellation is explicit', () => {
 const result = buildPracticeSchedule(parts, null, 99);
 assert.equal(result.events.length, 2);
 const session = { cancelled: false }; session.cancelled = true;
 assert.equal(sessionIsCurrent(session, session), false);
});

test('production schedule carries final starts and preserves trailing silent measures', () => {
 const result = buildPracticeSchedule([{ name: 'Tenor', events: [{ id: 'A', measure: 1, onset: 0, beats: 1 }, { id: 'B', measure: 2, onset: 1, beats: 1 }] }], { status: 'encoded', safeToApply: true, measureSequence: [1, 2, 3], measureStarts: { 1: 0, 2: 1, 3: 2 }, measureDurations: { 1: 1, 2: 1, 3: 4 } }, 2);
 assert.equal(result.duration, 12);
 assert.deepEqual(result.events.map((event) => `${event.id}@${event.scheduledOnset}`), ['A@0', 'B@1', 'A@6', 'B@7']);
});

test('guarded production pause action ignores cancellation after an async await', async () => {
 const session = { cancelled: false }; let resolve;
 const pending = new Promise((done) => { resolve = done; });
 const result = guardedAudioAction(() => pending, session, session);
 session.cancelled = true; resolve();
 assert.equal(await result, false);
});

test('incomplete shared timing fails closed without truncating a repeated measure', () => {
 const result = buildPracticeSchedule([{ name: 'Tenor', events: [{ id: 'A', measure: 1, onset: 0, beats: 1 }, { id: 'B', measure: 2, onset: 1, beats: 1 }] }], { status: 'encoded', safeToApply: true, measureSequence: [1, 2, 1], measureStarts: { 1: 0, 2: 1 }, measureDurations: { 1: 1 } }, 2);
 assert.equal(result.events.length, 2);
 assert.equal(result.duration, 2);
 assert.deepEqual(result.events.map((event) => `${event.id}@${event.scheduledOnset}`), ['A@0', 'B@1']);
});

test('unsafe or null timing never expands repeats', () => {
 const unsafe = buildPracticeSchedule([{ name: 'Tenor', events: [{ id: 'A', measure: 1, onset: 0, beats: 1 }, { id: 'B', measure: 2, onset: 1, beats: 1 }] }], { status: 'encoded', safeToApply: false, measureSequence: [1, 2], measureStarts: { 1: 0, 2: 1 }, measureDurations: { 1: 1, 2: 1 } }, 2);
 const nullStart = buildPracticeSchedule([{ name: 'Tenor', events: [{ id: 'A', measure: 1, onset: 0, beats: 1 }, { id: 'B', measure: 2, onset: 1, beats: 1 }] }], { status: 'encoded', safeToApply: true, measureSequence: [1, 2], measureStarts: { 1: null, 2: 1 }, measureDurations: { 1: 1, 2: 1 } }, 2);
 assert.deepEqual(unsafe.events.map((event) => event.id), ['A', 'B']);
 assert.deepEqual(nullStart.events.map((event) => event.id), ['A', 'B']);
});
