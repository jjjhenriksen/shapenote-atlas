import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { scoreToMusicXml, shapeForScoreEvent } from '../src/scoreMusicXml.js';
const event = (overrides = {}) => ({ step: 'C', octave: 5, onset: 0, beats: 1, measure: '1', staff: '1', voice: '1', type: 'quarter', ...overrides });
const score = (events, extra = {}) => ({ workTitle: 'Source <witness> & evidence', keySignature: '0:major', timeSignature: '4/4', parts: [{ name: 'Treble & source', clefs: { '1': 'treble' }, events }], ...extra });
function parsed(xml) {
  const result = spawnSync('python3', ['-c', `import sys,json,xml.etree.ElementTree as E
r=E.fromstring(sys.stdin.read())
print(json.dumps({'title':r.findtext('work/work-title'),'parts':[{'name':p.findtext('part-name')} for p in r.findall('part-list/score-part')],'pitches':[[n.findtext('pitch/step'),n.findtext('pitch/alter'),n.findtext('pitch/octave'),n.findtext('duration'),n.findtext('voice'),n.findtext('staff')] for n in r.findall('.//note')],'clefs':[[c.findtext('sign'),c.findtext('line')] for c in r.findall('.//clef')]}))`], { input: xml, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr); return JSON.parse(result.stdout);
}
test('MusicXML preserves written enharmonic pitches, rhythm, clefs and safe text', () => {
  const source = score([event({ step: 'B', alter: -1, octave: 4, type: 'half', beats: 3, dots: 1, notehead: 'fa', noteheadFilled: false })]);
  const before = JSON.stringify(source); const { xml, stats } = scoreToMusicXml(source);
  const data = parsed(xml);
  assert.deepEqual(data.pitches, [['B', '-1', '4', '3000', '1', '1']]);
  assert.deepEqual(data.clefs, [['G', '2']]);
  assert.equal(data.title, source.workTitle); assert.equal(data.parts[0].name, 'Treble & source');
  assert.match(xml, /<dot\/>/); assert.match(xml, /<notehead filled="no">triangle/);
  assert.equal(stats.source, 1); assert.equal(JSON.stringify(source), before);
});
test('flat transposition preserves Bb4 rather than respelling to A# or shifting octave', () => {
  const { xml } = scoreToMusicXml(score([event()]), { sourceKey: 'C major', targetKey: 'Bb', transpose: -2 });
  assert.deepEqual(parsed(xml).pitches[0].slice(0, 3), ['B', '-1', '4']);
  assert.match(xml, /<fifths>-2<\/fifths>/);
});
test('five parts and multi-staff C clefs retain source identities and simultaneous streams', () => {
  const source = score([], { parts: ['Treble', 'Alto', 'Tenor', 'Bass', 'Fifth'].map((name, i) => ({ name, clefs: { '1': ['treble', 'alto', 'tenor', 'bass', 'treble'][i] }, events: [event()] })) });
  source.parts[1].clefs['2'] = 'bass'; source.parts[1].events.push(event({ voice: '2', staff: '2', step: 'G', octave: 3 }));
  const { xml } = scoreToMusicXml(source); const data = parsed(xml);
  assert.equal(data.parts.length, 5); assert.deepEqual(data.clefs, [['G','2'],['C','3'],['F','4'],['C','4'],['F','4'],['G','2']]);
  assert.match(xml, /<backup><duration>1000<\/duration><\/backup>/);
  assert.ok(data.pitches.some((pitch) => pitch[4] === '2' && pitch[5] === '2'));
});
test('shape evidence is not inferred without a key; encoded normal stays round', () => {
  assert.deepEqual(shapeForScoreEvent(event(), ''), { name: '', kind: 'unavailable' });
  assert.equal(shapeForScoreEvent(event({ notehead: 'normal' }), 'C major').kind, 'source');
  assert.equal(shapeForScoreEvent(event({ step: 'A' }), 'A minor').name, 'la');
  const { xml } = scoreToMusicXml(score([event()], { keySignature: '' })); assert.doesNotMatch(xml, /<key>|<notehead/);
});
test('review collisions stay suppressed and unreviewed raw events remain unchanged', () => {
  const source = score([event(), event({ step: 'E' }), event({ onset: 1 })]);
  const result = scoreToMusicXml(source, { reviewDraft: true });
  assert.equal(result.stats.suppressed, 2); assert.equal(parsed(result.xml).pitches.length, 1);
  assert.equal(parsed(scoreToMusicXml(source).xml).pitches.length, 3);
});
test('invalid timing/pitch and unsupported clefs fail visibly instead of fabricating notes', () => {
  for (const override of [{ beats: null }, { beats: -1 }, { step: 'X' }, { clef: 'unsupported' }]) assert.throws(() => scoreToMusicXml(score([event(override)])));
  assert.throws(() => scoreToMusicXml({ parts: [] }));
});
for (const [name, path, count] of [['Devotion', 'draft-scores/sh2025-50t-devotion-v10.json',17], ['New Salem','draft-scores/kentucky-new-salem-v3.json',16], ['Salem','scores/a44b1cd022a09f20bdb403a3.json',19]]) {
  test(`${name} real witness serializes without source mutation`, () => {
    const source = JSON.parse(readFileSync(new URL(`../public/${path}`, import.meta.url))); const before = JSON.stringify(source);
    const { xml, measureCount } = scoreToMusicXml(source); assert.equal(measureCount,count); assert.equal(parsed(xml).parts.length,source.parts.length); assert.equal(JSON.stringify(source),before);
  });
}
