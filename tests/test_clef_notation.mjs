import test from 'node:test';
import assert from 'node:assert/strict';
import { STAFF_BOTTOM, CLEF_GLYPH, C_CLEF_CENTER } from '../src/clefNotation.js';

test('known pitches fall on their encoded clef reference lines', () => {
  const position = (diatonic, clef) => 16 - (diatonic - STAFF_BOTTOM[clef]) * 2;
  assert.equal(position(0, 'alto'), C_CLEF_CENTER.alto); // middle C, third line
  assert.equal(position(0, 'tenor'), C_CLEF_CENTER.tenor); // middle C, fourth line
  assert.equal(position(4, 'treble'), 12); // G4, second line
  assert.equal(position(-4, 'bass'), 4); // F3, fourth line
  assert.equal(CLEF_GLYPH.alto, '𝄡');
  assert.equal(CLEF_GLYPH.tenor, '𝄡');
  assert.equal(CLEF_GLYPH.treble, '𝄞');
  assert.equal(CLEF_GLYPH.bass, '𝄢');
});
