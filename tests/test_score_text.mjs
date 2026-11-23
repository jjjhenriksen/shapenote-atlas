import test from 'node:test';
import assert from 'node:assert/strict';
import { scoreText } from '../src/scoreText.js';

const event = (extra = {}) => ({ step: 'C', octave: 5, onset: 0, beats: 1, measure: '1', type: 'quarter', ...extra });
const score = (events, extra = {}) => ({ keySignature: 'C major', parts: [{ name: 'Treble', events }], ...extra });
const events = (result) => result.parts.flatMap((part) => part.measures.flatMap((measure) => measure.events.map((item) => item.text)));

test('score text preserves source pitch spelling, exact duration, lyric text and event order', () => {
  const source = score([event({ onset: 1, step: 'B', alter: -1, octave: 4, beats: 1.5, lyrics: [{ text: 'Light & hope', verse: '2' }] }), event()]);
  const before = JSON.stringify(source);
  assert.deepEqual(events(scoreText(source)), [
    'C octave 5; 1 quarter-note beat. Offset 0; voice 1, staff 1.',
    'B flat octave 4; 1.5 quarter-note beats. Offset 1; voice 1, staff 1. Verse 2: “Light & hope”.',
  ]);
  assert.equal(JSON.stringify(source), before);
});

test('transposed text follows displayed flat spelling and octave', () => {
  const result = scoreText(score([event()]), { sourceKey: 'C major', targetKey: 'Bb', transpose: -2 });
  assert.equal(result.transposed, true);
  assert.match(events(result)[0], /^B flat octave 4;/);
});

test('rests, grace notes and simultaneous streams stay explicit without creating lyric words', () => {
  const result = scoreText(score([event({ rest: true, step: undefined, octave: undefined }), event({ voice: '2', staff: '2', grace: true, beats: 0 }), event({ onset: 1 })]));
  assert.match(events(result)[0], /^Rest; 1 quarter-note beat/);
  assert.match(events(result)[1], /^C octave 5; grace note. Offset 0; voice 2, staff 2/);
  assert.ok(events(result).every((text) => !text.includes('Verse')));
});

test('review text omits the same ambiguous notes as engraving, preserving original lyric indices', () => {
  const source = score([event(), event({ step: 'E' }), event({ onset: 1 })]);
  source.parts[0].lyrics = [{ eventIndex: 0, text: 'Ambiguous' }, { eventIndex: 2, text: 'Clear' }];
  const result = scoreText(source, { reviewDraft: true });
  assert.equal(result.suppressed, 2);
  assert.equal(events(result).length, 1);
  assert.match(events(result)[0], /“Clear”/);
  assert.doesNotMatch(events(result)[0], /Ambiguous/);
  assert.equal(events(scoreText(source)).length, 3);
});

test('measure order and offsets follow per-part clocks, and empty measures stay unfilled', () => {
  const source = score([event({ measure: '2', onset: 4 }), event({ onset: 2 })]);
  source.parts[0].measureSemantics = [{ number: '2', onset: 4, end: 6 }, { number: '1', onset: 2, end: 4 }, { number: '3', onset: 6, end: 8 }];
  const result = scoreText(source);
  assert.deepEqual(result.parts[0].measures.map((measure) => measure.number), ['1', '2', '3']);
  assert.ok(events(result).every((text) => text.includes('Offset 0;')));
  assert.deepEqual(result.parts[0].measures[2].events, []);
});

test('lyric elisions, syllable spans and empty extenders preserve only encoded text', () => {
  const result = scoreText(score([event({ lyrics: [{ texts: ['Light', 'and'], elision: ['_'], syllabic: 'begin', number: '3', extend: { type: 'start' } }, { text: '', extend: true }] })]));
  assert.match(events(result)[0], /Verse 3: “Light_and”, begin syllable, lyric extender start/);
  assert.match(events(result)[0], /Verse 1: lyric extender/);
});

test('global lyric fallback respects source part identity and an explicitly empty lyric array', () => {
  const source = score([event(), event({ onset: 1, lyrics: [] })], { lyrics: [{ partId: 'P1', eventIndex: 0, text: 'Treble' }, { partId: 'P2', eventIndex: 0, text: 'Bass' }, { eventIndex: 1, text: 'Ignored' }] });
  assert.match(events(scoreText(source))[0], /“Treble”/);
  assert.doesNotMatch(events(scoreText(source))[0], /Bass/);
  assert.doesNotMatch(events(scoreText(source))[1], /Ignored/);
});

test('missing pitch/timing and incomplete lyrics fail like the engraving instead of guessing', () => {
  for (const extra of [{ step: undefined }, { beats: null }, { lyrics: [{ text: 'Light', elision: ['_'] }] }]) {
    assert.throws(() => scoreText(score([event(extra)])));
  }
  assert.throws(() => scoreText({ parts: [] }));
  assert.doesNotMatch(events(scoreText(score([event()], { keySignature: '' })))[0], /shape|major|minor/);
});
