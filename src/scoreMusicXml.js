// Atlas witness → MusicXML. Engraving never changes source/review authority.
import { parseKey, pitchToMidi, transposedNotation, STEP_SEMITONES, STEP_DIATONIC, DIATONIC_STEPS } from './notation.js';
import { sourceNoteheadEvidence, noteheadFilled } from './noteheadEvidence.js';

const DIVISIONS = 1000; // Atlas's parser records quarter-note beats to 3 decimals.
const SHAPES = ['fa', 'sol', 'la', 'fa', 'sol', 'la', 'mi'];
const HEADS = { fa: 'triangle', sol: 'normal', round: 'normal', la: 'square', mi: 'diamond' };
const CLEFS = { treble: ['G', 2], bass: ['F', 4], alto: ['C', 3], tenor: ['C', 4] };
const TYPES = new Set(['maxima', 'long', 'breve', 'whole', 'half', 'quarter', 'eighth', '16th', '32nd', '64th', '128th', '256th', '512th', '1024th']);
const ACCIDENTALS = new Set(['sharp', 'flat', 'natural', 'double-sharp', 'double-flat', 'quarter-flat', 'quarter-sharp', 'three-quarters-flat', 'three-quarters-sharp']);
export const xmlText = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[char]));
const tag = (name, value) => `<${name}>${xmlText(value)}</${name}>`;
function ticks(value) {
  if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) || Number(value) < 0) throw new Error('Source timing is unavailable or invalid.');
  return Math.round(Number(value) * DIVISIONS);
}
export function shapeForScoreEvent(event, sourceKey) {
  const encoded = sourceNoteheadEvidence(event);
  if (encoded) return encoded;
  const key = parseKey(sourceKey);
  if (!key || !event.step) return { name: '', kind: 'unavailable' };
  const root = key.mode === 'minor' ? DIATONIC_STEPS[(STEP_DIATONIC[key.tonicStep] + 2) % 7] : key.tonicStep;
  return { name: SHAPES[(STEP_DIATONIC[event.step] - STEP_DIATONIC[root] + 7) % 7], kind: 'derived' };
}

function keyXml(sourceKey, targetKey, transpose) {
  const source = parseKey(sourceKey);
  const key = transpose && targetKey ? parseKey(`${parseKey(targetKey)?.rootName || targetKey} ${source?.mode || 'major'}`) : source;
  if (!key) return '';
  const roots = key.mode === 'minor' ? ['Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#'] : ['Cb', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#'];
  const fifths = roots.indexOf(key.rootName) - 7;
  return roots.includes(key.rootName) ? `<key>${tag('fifths', fifths)}${tag('mode', key.mode)}</key>` : '';
}
function clefXml(clef, number) {
  if (!CLEFS[clef]) throw new Error(`Unsupported source clef: ${clef}`);
  const [sign, line] = CLEFS[clef];
  return `<clef number="${number}">${tag('sign', sign)}${tag('line', line)}</clef>`;
}

export function scoreMeasures(score) {
  const measures = new Map();
  for (const part of score.parts || []) {
    for (const measure of part.measureSemantics || []) {
      const key = String(measure.number);
      const start = ticks(measure.onset);
      const end = measure.durationAvailable && measure.duration != null ? start + ticks(measure.duration) : ticks(measure.end);
      const previous = measures.get(key);
      if (previous && (previous.start !== start || previous.end !== end)) throw new Error('Source parts disagree on measure timing.');
      measures.set(key, { number: key, start, end });
    }
  }
  const events = (score.parts || []).flatMap((part) => part.events || []);
  for (const event of events) {
    const number = String(event.measure ?? '1');
    const start = ticks(event.onset), end = start + ticks(event.beats);
    if (!measures.has(number)) measures.set(number, { number, start, end, inferred: true });
    else if (measures.get(number).inferred) {
      const m = measures.get(number); m.start = Math.min(m.start, start); m.end = Math.max(m.end, end);
    }
  }
  return [...measures.values()].sort((a, b) => a.start - b.start);
}

function noteXml(event, options, chord, staff, voice) {
  const { sourceKey, targetKey, transpose } = options;
  const duration = ticks(event.beats);
  if (!duration && !event.grace) throw new Error('Source note duration is unavailable or zero.');
  const isRest = event.rest === true;
  const notation = transposedNotation(event, sourceKey, targetKey, transpose);
  const originalMidi = pitchToMidi(event);
  if (!isRest && (!Object.hasOwn(STEP_SEMITONES, notation.step) || !Number.isInteger(notation.octave) || !Number.isFinite(originalMidi))) throw new Error('Source pitch is unavailable or invalid.');
  const alter = transpose ? originalMidi + transpose - (12 * (notation.octave + 1) + STEP_SEMITONES[notation.step]) : Number(event.alter || 0);
  const pitch = isRest ? '<rest/>' : `<pitch>${tag('step', notation.step)}${alter ? tag('alter', alter) : ''}${tag('octave', notation.octave)}</pitch>`;
  const shape = shapeForScoreEvent(event, sourceKey);
  const head = !isRest && HEADS[shape.name] ? `<notehead filled="${noteheadFilled(event) ? 'yes' : 'no'}">${HEADS[shape.name]}</notehead>` : '';
  const accidental = ACCIDENTALS.has(notation.accidental) ? tag('accidental', notation.accidental) : '';
  return `<note>${event.grace ? '<grace/>' : ''}${chord ? '<chord/>' : ''}${pitch}${event.grace ? '' : tag('duration', duration)}${tag('voice', voice)}${TYPES.has(event.type) ? tag('type', event.type) : ''}${'<dot/>'.repeat(Math.max(0, Math.min(3, Number(event.dots) || 0)))}${accidental}${head}${tag('staff', staff)}</note>`;
}

export function scoreToMusicXml(score, { sourceKey = score?.keySignature || '', targetKey = '', transpose = 0, reviewDraft = false } = {}) {
  if (!score?.parts?.length) throw new Error('No source parts are available for engraving.');
  if (!Number.isFinite(transpose)) throw new Error('Invalid transposition.');
  const options = { sourceKey, targetKey, transpose };
  const measures = scoreMeasures(score);
  if (!measures.length) throw new Error('No source measures are available for engraving.');
  const stats = { source: 0, derived: 0, unavailable: 0, suppressed: 0 };
  const parts = score.parts.map((part, partIndex) => {
    const staffIds = [...new Set([...Object.keys(part.clefs || {}), ...(part.events || []).map((e) => String(e.staff || '1'))])];
    const staffNumber = (id) => staffIds.indexOf(String(id || '1')) + 1;
    const clefs = new Map(staffIds.map((id) => [id, part.clefs?.[id] || part.events?.find((e) => String(e.staff || '1') === id && e.clef)?.clef || 'treble']));
    const collisions = new Map();
    for (const e of part.events || []) if (!e.rest) { const key = `${e.measure}|${e.onset}`; collisions.set(key, (collisions.get(key) || 0) + 1); }
    const indexed = (part.events || []).map((event, index) => ({ event, index })).filter(({ event }) => {
      if (reviewDraft && !event.rest && collisions.get(`${event.measure}|${event.onset}`) > 1) { stats.suppressed++; return false; }
      if (!event.rest) stats[shapeForScoreEvent(event, sourceKey).kind]++;
      return true;
    });
    const music = measures.map((measure, measureIndex) => {
      const events = indexed.filter(({ event }) => String(event.measure ?? '1') === measure.number);
      const time = String(score.timeSignature || '').match(/^(\d+(?:\+\d+)*)\/(\d+)$/);
      const attributes = measureIndex === 0 ? `<attributes>${tag('divisions', DIVISIONS)}${keyXml(sourceKey, targetKey, transpose)}${time ? `<time>${tag('beats', time[1])}${tag('beat-type', time[2])}</time>` : ''}${tag('staves', staffIds.length)}${staffIds.map((id) => clefXml(clefs.get(id), staffNumber(id))).join('')}</attributes>` : '';
      const streams = new Map();
      for (const item of events) { const key = `${item.event.voice || '1'}|${item.event.staff || '1'}`; if (!streams.has(key)) streams.set(key, []); streams.get(key).push(item); }
      let content = '', cursor = 0;
      for (const stream of streams.values()) {
        if (cursor) content += `<backup>${tag('duration', cursor)}</backup>`;
        cursor = 0; let previous = null;
        for (const { event, index } of stream.sort((a, b) => Number(a.event.onset) - Number(b.event.onset) || a.index - b.index)) {
          const onset = ticks(event.onset) - measure.start;
          if (onset < 0) throw new Error('Source event starts before its measure.');
          const chord = previous && ticks(previous.onset) === ticks(event.onset) && !event.rest && !previous.rest;
          if (!chord && onset !== cursor) content += `<${onset > cursor ? 'forward' : 'backup'}>${tag('duration', Math.abs(onset - cursor))}</${onset > cursor ? 'forward' : 'backup'}>`;
          const staffId = String(event.staff || '1');
          if (event.clef && event.clef !== clefs.get(staffId)) { content += `<attributes>${clefXml(event.clef, staffNumber(staffId))}</attributes>`; clefs.set(staffId, event.clef); }
          content += noteXml(event, options, chord, staffNumber(staffId), event.voice || '1');
          if (!chord) cursor = onset + (event.grace ? 0 : ticks(event.beats));
          previous = event;
        }
      }
      // Preserve empty measures/trailing silence without adding fabricated notes.
      if (cursor < measure.end - measure.start) content += `<forward>${tag('duration', measure.end - measure.start - cursor)}</forward>`;
      return `<measure number="${xmlText(measure.number)}" implicit="yes">${attributes}${content}</measure>`;
    }).join('');
    return `<part id="P${partIndex + 1}">${music}</part>`;
  });
  const list = score.parts.map((part, index) => `<score-part id="P${index + 1}">${tag('part-name', part.name || `Part ${index + 1}`)}</score-part>`).join('');
  return { xml: `<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"><work>${tag('work-title', score.workTitle || 'Available source score')}</work><part-list>${list}</part-list>${parts.join('')}</score-partwise>`, stats, measureCount: measures.length };
}
