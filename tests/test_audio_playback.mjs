import test from 'node:test';
import assert from 'node:assert/strict';
import { createAudioState, disposeAudio, schedulePracticeAudio, stopAudioResources, SCHEDULE_HORIZON_SECONDS } from '../src/audioPlayback.js';
import { buildPracticeSchedule } from '../src/practice.js';

function fixture() {
  let nextTimer = 1;
  const callbacks = new Map();
  const timers = { setInterval: (fn) => { const id = nextTimer++; callbacks.set(id, fn); return id; }, clearInterval: (id) => callbacks.delete(id) };
  const allocated = [], starts = [], allNodes = [];
  const sounding = new Set();
  const parameter = () => ({ value: 0, setValueAtTime() {}, linearRampToValueAtTime() {}, setTargetAtTime() {} });
  const node = () => { const value = { disconnected: false, connect() {}, disconnect() { this.disconnected = true; } }; allNodes.push(value); return value; };
  const context = { currentTime: 0, state: 'running', destination: {}, closed: 0,
    createGain: () => ({ ...node(), gain: parameter() }), createStereoPanner: () => ({ ...node(), pan: parameter() }),
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
  return { audio, session, context, timers, callbacks, allocated, starts, allNodes, schedule, advance };
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
