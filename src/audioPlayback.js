import { sessionIsCurrent } from './practice.js';

export const SCHEDULE_HORIZON_SECONDS = 0.5;
export const SCHEDULE_INTERVAL_MS = 25;

export function createAudioState() {
  return { context: null, master: null, nodes: new Set(), schedulerTimer: null, progressTimer: null, generation: 0, session: null, disposed: false };
}

export function stopAudioResources(audio, timers = globalThis) {
  if (audio.session) audio.session.cancelled = true;
  audio.session = null;
  audio.generation += 1;
  for (const key of ['schedulerTimer', 'progressTimer']) {
    if (audio[key] !== null) timers.clearInterval(audio[key]);
    audio[key] = null;
  }
  for (const voice of [...audio.nodes]) voice.release(true);
  if (audio.master) { try { audio.master.disconnect(); } catch {} }
  audio.master = null;
}

export function disposeAudio(audio, timers = globalThis) {
  audio.disposed = true;
  stopAudioResources(audio, timers);
  const context = audio.context;
  audio.context = null;
  if (context && context.state !== 'closed') {
    try { Promise.resolve(context.close()).catch(() => {}); } catch {}
  }
}

// Events retain the repeat/loop planner's exact onset. Only node allocation is
// incremental; the audio clock also freezes the horizon during pause.
export function schedulePracticeAudio(audio, session, events, {
  startedAt, beatSeconds, partNames, pitchToMidi, transpose = 0,
  onError, timers = globalThis,
}) {
  const context = audio.context;
  const current = () => !audio.disposed && sessionIsCurrent(audio.session, session) && audio.generation === session.generation;
  const queue = events.filter((event) => {
    const midi = pitchToMidi(event);
    return !event.rest && midi !== null && Number.isFinite(midi)
      && Number.isFinite(Number(event.scheduledOnset)) && Number(event.scheduledOnset) >= 0
      && Number.isFinite(Number(event.beats)) && Number(event.beats) > 0;
  }).sort((a, b) => Number(a.scheduledOnset) - Number(b.scheduledOnset));
  if (!current() || !queue.length) return false;
  const master = context.createGain();
  audio.master = master;
  master.gain.setValueAtTime(0.78, startedAt);
  master.connect(context.destination);
  let cursor = 0;
  function tick() {
    if (!current()) return;
    try {
      const horizon = context.currentTime + SCHEDULE_HORIZON_SECONDS;
      while (cursor < queue.length && startedAt + Number(queue[cursor].scheduledOnset) * beatSeconds <= horizon) {
        const event = queue[cursor++];
        const nominalStart = startedAt + Number(event.scheduledOnset) * beatSeconds;
        const duration = Math.max(0.12, Number(event.beats) * beatSeconds * 0.9);
        // A throttled/background tab must not burst already-finished notes.
        if (nominalStart + duration + 0.15 <= context.currentTime) continue;
        const voice = { oscillator: null, gain: null, pan: null, released: false, release(stop = false) {
          if (this.released) return;
          this.released = true;
          if (this.oscillator) {
            this.oscillator.onended = null;
            if (stop) { try { this.oscillator.stop(); } catch {} }
          }
          for (const node of [this.oscillator, this.gain, this.pan]) { if (node) { try { node.disconnect(); } catch {} } }
          audio.nodes.delete(this);
        } };
        // Register before allocation so any partial chain is cleaned on error.
        audio.nodes.add(voice);
        const oscillator = voice.oscillator = context.createOscillator();
        const gain = voice.gain = context.createGain();
        const pan = voice.pan = context.createStereoPanner ? context.createStereoPanner() : null;
        const partIndex = partNames.indexOf(event.partName);
        oscillator.type = partIndex % 2 ? 'triangle' : 'sine';
        oscillator.frequency.value = 440 * Math.pow(2, (pitchToMidi(event) + transpose - 69) / 12);
        const start = Math.max(context.currentTime + 0.02, nominalStart);
        const noteLevel = Math.min(0.18, 0.72 / Math.max(partNames.length, 1));
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(noteLevel, start + 0.025);
        gain.gain.setTargetAtTime(0, start + duration * 0.72, 0.08);
        oscillator.connect(gain);
        if (pan) { pan.pan.value = (partIndex - (partNames.length - 1) / 2) * 0.22; gain.connect(pan); pan.connect(master); }
        else gain.connect(master);
        oscillator.onended = () => voice.release();
        oscillator.start(start);
        oscillator.stop(start + duration + 0.15);
      }
      if (cursor === queue.length && audio.schedulerTimer !== null) {
        timers.clearInterval(audio.schedulerTimer);
        audio.schedulerTimer = null;
      }
    } catch (error) {
      stopAudioResources(audio, timers);
      onError(error);
    }
  }
  audio.schedulerTimer = timers.setInterval(tick, SCHEDULE_INTERVAL_MS);
  tick();
  return current();
}
