import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildPracticeSchedule, canApplyPlaybackPlan, resolveRepeatPlayback, guardedAudioAction, resolvePlaybackQuarantine, scheduleWithCleanup, sessionIsCurrent, shouldCompleteSession } from '../src/practice.js';

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
 assert.equal(result.events.length, 16);
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


test('New Salem terminal repeat follows its source contract without editing the score', () => {
 const score = JSON.parse(readFileSync(new URL('../public/draft-scores/kentucky-new-salem-v3.json', import.meta.url)));
 const before = JSON.stringify(score);
 const plan = resolveRepeatPlayback(score);
 assert.equal(canApplyPlaybackPlan(plan), true);
 const measures = Array.from({ length: 16 }, (_, i) => String(i + 1));
 assert.deepEqual(plan.measureSequence, [...measures, ...measures]);
 const written = buildPracticeSchedule(score.parts, null);
 const repeated = buildPracticeSchedule(score.parts, plan);
 assert.equal(written.duration, 64);
 assert.equal(written.events.filter((event) => !event.rest).length, 167);
 assert.equal(repeated.duration, 128);
 assert.equal(repeated.events.filter((event) => !event.rest).length, 334);
 assert.deepEqual(repeated.events.slice(0, 42), written.events.slice(0, 42));
 assert.equal(JSON.stringify(score), before);
 const loops = buildPracticeSchedule(score.parts, plan, 2);
 assert.equal(loops.duration, 256);
 assert.equal(loops.events.filter((event) => !event.rest).length, 668);
});

test('Something New has no encoded repeat but permits deliberate written-order practice loops', () => {
 const score = JSON.parse(readFileSync(new URL('../public/draft-scores/shenandoah-something-new-v3.json', import.meta.url)));
 assert.equal(canApplyPlaybackPlan(resolveRepeatPlayback(score)), false);
 const result = buildPracticeSchedule(score.parts, null, 2);
 assert.equal(result.duration, 90);
 assert.equal(result.events.filter((event) => !event.rest).length, 470);
});

test('unsupported navigation and blocked plans cannot enable source repeat playback', () => {
 const encoded = { status: 'encoded', safeToApply: true, measureSequence: ['1'], measureStarts: { '1': 0 }, measureDurations: { '1': 4 } };
 assert.equal(canApplyPlaybackPlan(resolveRepeatPlayback({ semanticContract: { playback: encoded }, soundNavigation: [{ dacapo: 'yes' }] })), false);
 assert.equal(canApplyPlaybackPlan(resolveRepeatPlayback({ playback: { status: 'blocked', safeToApply: false }, semanticContract: { playback: encoded } })), false);
 assert.equal(canApplyPlaybackPlan({ ...encoded, measureStarts: { '1': null } }), false);
});
