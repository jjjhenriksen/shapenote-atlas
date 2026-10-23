import test from 'node:test';
import assert from 'node:assert/strict';
import { createAudioState, disposeAudio, schedulePracticeAudio, stopAudioResources, SCHEDULE_HORIZON_SECONDS } from '../src/audioPlayback.js';
import { buildPracticeSchedule } from '../src/practice.js';

function fixture() {
  let nextTimer = 1;
  const callbacks = new Map();
  const timers = { setInterval: (fn) => { const id = nextTimer++; callbacks.set(id, fn); return id; }, clearInterval: (id) => callbacks.delete(id) };
  const allocated = [], starts = [], allNodes = [], gains = [];
  const sounding = new Set();
  const parameter = () => ({ value: 0, automation: [],
    setValueAtTime(value, at) { this.automation.push({ method: 'set', value, at }); },
    linearRampToValueAtTime(value, at) { this.automation.push({ method: 'ramp', value, at }); },
    setTargetAtTime(value, at, timeConstant) { this.automation.push({ method: 'target', value, at, timeConstant }); },
  });
  const node = () => { const value = { disconnected: false, connect() {}, disconnect() { this.disconnected = true; } }; allNodes.push(value); return value; };
  const context = { currentTime: 0, state: 'running', destination: {}, closed: 0,
    createGain: () => { const gain = { ...node(), gain: parameter() }; gains.push(gain); return gain; }, createStereoPanner: () => ({ ...node(), pan: parameter() }),
    createOscillator() { const osc = { ...node(), frequency: parameter(), stops: [], start(at) { starts.push(at); }, stop(at) { this.stops.push(at); this.endsAt = at ?? context.currentTime; } }; allocated.push(osc); sounding.add(osc); return osc; },
    close() { this.state = 'closed'; this.closed++; return Promise.resolve(); },
  };
  const audio = createAudioState(); audio.context = context;
  const session = { generation: audio.generation, cancelled: false }; audio.session = session;
  function advance(at) {
    context.currentTime = at;
    for (const osc of sounding) if (osc.endsAt <= at) { sounding.delete(osc); if (osc.onended) osc.onended(); }
    for (const fn of [...callbacks.values()]) fn();
  }
  function schedule(events, options = {}) { return schedulePracticeAudio(audio, session, events, { startedAt: 0.08, beatSeconds: 0.5, partNames: ['Tenor'], pitchToMidi: (event) => event.rest ? null : 60, timers, onError: (error) => { throw error; }, ...options }); }
  return { audio, session, context, timers, callbacks, allocated, starts, allNodes, gains, schedule, advance };
}

test('eight loops of a long four-part score retain only the horizon and sounding notes', () => {
  const f = fixture();
  const names = ['Treble', 'Alto', 'Tenor', 'Bass'];
  const parts = names.map((name) => ({ name, events: Array.from({ length: 2000 }, (_, onset) => ({ onset, beats: 1, step: 'C' })) }));
  const plan = buildPracticeSchedule(parts, null, 8);
  assert.equal(plan.events.length, 64000);
  assert.equal(f.schedule(plan.events, { partNames: names }), true);
  assert.equal(f.allocated.length, 4);
  let peak = f.audio.nodes.size;
  for (let time = 0.025; time < 8001; time += 0.025) {
    f.advance(time); peak = Math.max(peak, f.audio.nodes.size);
  }
  assert.ok(peak <= 12, `peak retained voices ${peak}`);
  assert.equal(f.allocated.length, 64000);
  assert.equal(f.audio.nodes.size, 0);
  assert.equal(f.audio.schedulerTimer, null);
  assert.equal(f.callbacks.size, 0);
});

test('incremental starts match encoded repeats, trailing silence, and loop offsets', () => {
  const f = fixture();
  const parts = [{ name: 'Tenor', events: [{ measure: 1, onset: 0, beats: 1 }, { measure: 2, onset: 1, beats: 1 }] }];
  const plan = buildPracticeSchedule(parts, { status: 'encoded', safeToApply: true, measureSequence: [1, 2, 1, 3], measureStarts: { 1: 0, 2: 1, 3: 2 }, measureDurations: { 1: 1, 2: 1, 3: 4 } }, 2);
  assert.equal(plan.duration, 14);
  f.schedule(plan.events);
  for (let at = 0.025; at <= 8; at += 0.025) f.advance(at);
  assert.deepEqual(f.starts, plan.events.map((event) => 0.08 + event.scheduledOnset * 0.5));
});

test('stop cancels scheduler and disconnects every active chain immediately', () => {
  const f = fixture();
  f.schedule([{ scheduledOnset: 0, beats: 1 }, { scheduledOnset: 10, beats: 1 }]);
  const voices = [...f.audio.nodes]; const master = f.audio.master;
  stopAudioResources(f.audio, f.timers);
  assert.equal(f.callbacks.size, 0);
  assert.equal(f.audio.nodes.size, 0);
  assert.equal(f.session.cancelled, true);
  assert.equal(master.disconnected, true);
  for (const voice of voices) for (const node of [voice.oscillator, voice.gain, voice.pan]) assert.equal(node.disconnected, true);
  f.advance(20);
  assert.equal(f.allocated.length, 1);
});

test('pause freezes lookahead and late wake skips completed notes', () => {
  const f = fixture();
  f.schedule(Array.from({ length: 100 }, (_, scheduledOnset) => ({ scheduledOnset, beats: 1 })));
  f.advance(0); f.advance(0);
  assert.equal(f.allocated.length, 1);
  f.advance(40);
  assert.ok(f.allocated.length <= 4);
  assert.ok(f.starts.slice(1).every((at) => at >= 40));
  assert.equal(SCHEDULE_HORIZON_SECONDS, 0.5);
});


function closeTo(actual, expected) {
  assert.ok(Math.abs(actual - expected) < 1e-9, `expected ${expected}, received ${actual}`);
}

test('late wake keeps nominal release and stop deadlines without overlapping the next note', () => {
  const f = fixture();
  f.schedule([{ scheduledOnset: 2, beats: 4 }, { scheduledOnset: 6, beats: 1 }], { startedAt: 0 });
  assert.equal(f.allocated.length, 0);
  f.advance(2);
  assert.equal(f.allocated.length, 1);
  closeTo(f.starts[0], 2.02);
  const envelope = f.gains[1].gain.automation;
  closeTo(envelope.find(event => event.method === 'ramp').at, 2.045);
  closeTo(envelope.find(event => event.method === 'target').at, 2.296);
  closeTo(f.allocated[0].endsAt, 2.95);
  f.advance(2.5);
  assert.equal(f.allocated.length, 2);
  closeTo(f.starts[1], 3);
  assert.ok(f.allocated[0].endsAt <= f.starts[1], 'late first note must finish before the next nominal onset');
  f.advance(2.95);
  assert.equal(f.audio.nodes.size, 1);
  f.advance(3.6);
  assert.equal(f.audio.nodes.size, 0);
});

test('late attack shortens to the nominal release deadline', () => {
  const f = fixture();
  f.schedule([{ scheduledOnset: 2, beats: 4 }], { startedAt: 0 });
  f.advance(2.27);
  closeTo(f.starts[0], 2.29);
  const envelope = f.gains[1].gain.automation;
  closeTo(envelope.find(event => event.method === 'ramp').at, 2.296);
  closeTo(envelope.find(event => event.method === 'target').at, 2.296);
  closeTo(f.allocated[0].endsAt, 2.95);
  assert.ok(envelope.every(event => event.at >= f.starts[0]));
});

test('late wake skips notes already in release rather than replaying their decay tails', () => {
  for (const at of [2.28, 2.8, 4]) {
    const f = fixture();
    f.schedule([{ scheduledOnset: 2, beats: 4 }], { startedAt: 0 });
    f.advance(at);
    assert.equal(f.allocated.length, 0, `wake at ${at} must not start an elapsed envelope`);
    assert.equal(f.audio.nodes.size, 0);
    assert.equal(f.audio.schedulerTimer, null);
  }
});

test('late tied notes retain their distinct release fraction and nominal stop', () => {
  const f = fixture();
  f.schedule([{ scheduledOnset: 2, beats: 4, tiedSegments: 2 }], { startedAt: 0 });
  f.advance(2);
  closeTo(f.starts[0], 2.02);
  const release = f.gains[1].gain.automation.find(event => event.method === 'target');
  closeTo(release.at, 2.94);
  closeTo(f.allocated[0].endsAt, 3.15);
  assert.equal(release.timeConstant, 0.08);
});

test('dispose closes the owned context once and rejects stale work', () => {
  const f = fixture();
  f.schedule([{ scheduledOnset: 0, beats: 1 }]);
  f.audio.progressTimer = f.timers.setInterval(() => {});
  disposeAudio(f.audio, f.timers); disposeAudio(f.audio, f.timers);
  assert.equal(f.context.closed, 1);
  assert.equal(f.callbacks.size, 0);
  assert.equal(f.audio.context, null);
  assert.equal(f.audio.disposed, true);
  assert.equal(f.schedule([{ scheduledOnset: 0, beats: 1 }]), false);
});

test('a partial allocation failure releases all prior voices and the master', () => {
  const f = fixture(); let calls = 0;
  const create = f.context.createGain;
  f.context.createGain = () => { if (++calls === 3) throw new Error('gain failed'); return create(); };
  assert.throws(() => f.schedule([{ scheduledOnset: 0, beats: 1 }, { scheduledOnset: 0, beats: 1 }]), /gain failed/);
  assert.equal(f.audio.nodes.size, 0);
  assert.equal(f.audio.master, null);
  assert.equal(f.callbacks.size, 0);
  assert.ok(f.allocated.every((node) => node.disconnected));
});
