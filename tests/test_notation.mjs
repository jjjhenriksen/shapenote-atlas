import test from 'node:test';
import assert from 'node:assert/strict';
import { parseKey, pitchToMidi, transposedNotation } from '../src/notation.js';

const alterations = { '': 0, flat: -1, 'double-flat': -2, sharp: 1, 'double-sharp': 2 };

for (const [label, event, source, target, shift, expected] of [
  ['C5 to Bb4', { step: 'C', octave: 5 }, 'C major', 'Bb major', -2, { step: 'B', octave: 4, accidental: 'flat' }],
  ['C4 to Db4', { step: 'C', octave: 4 }, 'C major', 'Db major', 1, { step: 'D', octave: 4, accidental: 'flat' }],
  ['Cb4 to Bbb3', { step: 'C', octave: 4, alter: -1 }, 'C major', 'Bb major', -2, { step: 'B', octave: 3, accidental: 'double-flat' }],
  ['B3 crosses to C4', { step: 'B', octave: 3 }, 'C major', 'Db major', 1, { step: 'C', octave: 4, accidental: '' }],
  ['C4 crosses to B3', { step: 'C', octave: 4 }, 'C major', 'B major', -1, { step: 'B', octave: 3, accidental: '' }],
  ['B sharp crosses to C sharp', { step: 'B', octave: 3, alter: 1 }, 'C major', 'Db major', 1, { step: 'C', octave: 4, accidental: 'sharp' }],
  ['sharp-key control', { step: 'C', octave: 4 }, 'C major', 'C# major', 1, { step: 'C', octave: 4, accidental: 'sharp' }],
  ['double-sharp control', { step: 'C', octave: 4, alter: 1 }, 'C major', 'C# major', 1, { step: 'C', octave: 4, accidental: 'double-sharp' }],
]) {
  test(`transposed notation preserves the pitch of ${label}`, () => {
    const original = { ...event };
    const result = transposedNotation(event, source, target, shift);
    assert.deepEqual(result, expected);
    assert.equal(pitchToMidi({ ...result, alter: alterations[result.accidental] }), pitchToMidi(event) + shift);
    assert.deepEqual(event, original);
  });
}

test('encoded key signatures use the same flat spelling as named keys', () => {
  assert.deepEqual(transposedNotation({ step: 'C', octave: 5 }, '0:major', '-2:major', -2), {
    step: 'B', octave: 4, accidental: 'flat',
  });
  assert.equal(parseKey('-2:major').rootName, 'Bb');
});

test('no transposition and unavailable key evidence retain source notation', () => {
  const event = { step: 'E', octave: 4, alter: -1, accidental: 'flat' };
  const expected = { step: 'E', octave: 4, accidental: 'flat' };
  assert.deepEqual(transposedNotation(event, 'C', 'C', 0), expected);
  assert.deepEqual(transposedNotation(event, '', 'D', 2), expected);
});
