import { scoreMeasures, scoreToMusicXml } from './scoreMusicXml.js';
import { pitchToMidi, STEP_SEMITONES, transposedNotation } from './notation.js';

const ALTER_NAMES = new Map([[-2, 'double flat'], [-1.5, 'three-quarter flat'], [-1, 'flat'], [-0.5, 'quarter flat'], [0.5, 'quarter sharp'], [1, 'sharp'], [1.5, 'three-quarter sharp'], [2, 'double sharp']]);
const rounded = (value) => Math.round(Number(value) * 1000) / 1000;

function pitchText(event, { sourceKey, targetKey, transpose }) {
  if (event.rest) return 'Rest';
  const pitch = transposedNotation(event, sourceKey, targetKey, transpose);
  const alter = transpose
    ? pitchToMidi(event) + transpose - (12 * (pitch.octave + 1) + STEP_SEMITONES[pitch.step])
    : Number(event.alter || 0);
  const alteration = alter === 0 ? '' : ALTER_NAMES.get(alter) || `altered ${alter > 0 ? '+' : ''}${alter} semitones`;
  return [pitch.step, alteration, `octave ${pitch.octave}`].filter(Boolean).join(' ');
}

function lyricText(lyric) {
  const texts = lyric.texts || [lyric.text || ''];
  const text = texts.map((value, index) => `${index ? lyric.elision?.[index - 1] || ' ' : ''}${value}`).join('');
  const items = [];
  if (text) items.push(`“${text}”`);
  if (['begin', 'middle', 'end'].includes(lyric.syllabic)) items.push(`${lyric.syllabic} syllable`);
  if (lyric.extend === true || (lyric.extend && typeof lyric.extend === 'object')) {
    const type = ['start', 'continue', 'stop'].includes(lyric.extend?.type) ? ` ${lyric.extend.type}` : '';
    items.push(`lyric extender${type}`);
  }
  return items.length ? `Verse ${lyric.number || lyric.verse || '1'}: ${items.join(', ')}.` : '';
}

// The same conversion gate keeps this alternative aligned with the engraving:
// invalid pitch/timing and incomplete elisions never become plausible text.
// Text describes recorded events, not unencoded rests or inferred lyric words.
export function scoreText(score, { sourceKey = score?.keySignature || '', targetKey = '', transpose = 0, reviewDraft = false } = {}) {
  const options = { sourceKey, targetKey, transpose, reviewDraft };
  const { stats } = scoreToMusicXml(score, options);
  const measures = scoreMeasures(score);
  return {
    transposed: transpose !== 0,
    suppressed: stats.suppressed,
    parts: score.parts.map((part, partIndex) => {
      const collisions = new Map();
      for (const event of part.events || []) {
        if (!event.rest) {
          const key = `${event.measure}|${event.onset}`;
          collisions.set(key, (collisions.get(key) || 0) + 1);
        }
      }
      const indexed = (part.events || []).map((event, index) => ({ event, index }))
        .filter(({ event }) => !reviewDraft || event.rest || collisions.get(`${event.measure}|${event.onset}`) <= 1);
      return {
        name: part.name || `Part ${partIndex + 1}`,
        measures: measures.map((measure) => {
          const local = part.measureSemantics?.find((item) => String(item.number) === measure.number);
          const start = local ? rounded(local.onset) : measure.start / 1000;
          return {
            number: measure.number,
            events: indexed.filter(({ event }) => String(event.measure ?? '1') === measure.number)
              .sort((a, b) => Number(a.event.onset) - Number(b.event.onset) || a.index - b.index)
              .map(({ event, index }) => {
                const timing = event.grace ? 'grace note' : `${rounded(event.beats)} quarter-note ${rounded(event.beats) === 1 ? 'beat' : 'beats'}`;
                const context = `Offset ${rounded(rounded(event.onset) - start)}; voice ${event.voice || '1'}, staff ${event.staff || '1'}`;
                const lyrics = event.lyrics || (part.lyrics || score.lyrics || []).filter((lyric) => lyric.eventIndex === index && (!lyric.partId || lyric.partId === (part.id || `P${partIndex + 1}`)));
                return { index, text: `${pitchText(event, options)}; ${timing}. ${context}.${lyrics.length ? ` ${lyrics.map(lyricText).filter(Boolean).join(' ')}` : ''}` };
              }),
          };
        }),
      };
    }),
  };
}
