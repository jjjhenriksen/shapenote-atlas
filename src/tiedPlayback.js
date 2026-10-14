import { pitchToMidi } from './notation.js';

const near = (a, b) => Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) < 0.001;
// Call separately for each part and practice-loop visit. Require both audible
// adjacency and source adjacency, so a repeat jump cannot create a new tie.
export function coalesceSourceTies(events, sourceOnsetFor = (event) => Number(event.onset)) {
  const result = [], pending = new Map();
  const ordered = (events || []).map((event, index) => ({ event, index })).sort((a, b) => Number(a.event.onset) - Number(b.event.onset) || a.index - b.index);
  for (const { event } of ordered) {
    const midi = pitchToMidi(event);
    const onset = Number(event.onset), beats = Number(event.beats), sourceOnset = sourceOnsetFor(event);
    const key = JSON.stringify([event.voice || '1', event.staff || '1', event.step, event.alter || 0, event.octave]);
    if (event.rest) {
      for (const [id, candidate] of pending) if (candidate.voice === (event.voice || '1') && candidate.staff === (event.staff || '1')) pending.delete(id);
    }
    const previous = pending.get(key);
    const contiguous = previous && event.tieStop === true && previous.tieStart === true
      && near(previous.onset + previous.beats, onset) && near(previous.sourceEnd, sourceOnset);
    if (!event.rest && Number.isFinite(midi) && beats > 0 && contiguous) {
      previous.output.beats = Number(previous.output.beats) + beats;
      previous.output.tiedSegments = (previous.output.tiedSegments || 1) + 1;
      previous.onset = onset; previous.beats = beats; previous.sourceEnd = sourceOnset + beats; previous.tieStart = event.tieStart === true;
      if (!previous.tieStart) pending.delete(key);
    } else {
      const output = { ...event }; result.push(output);
      if (!event.rest && Number.isFinite(midi) && beats > 0 && event.tieStart === true) pending.set(key, { voice: event.voice || '1', staff: event.staff || '1', output, onset, beats, sourceEnd: sourceOnset + beats, tieStart: true });
      else pending.delete(key);
    }
  }
  return result;
}
