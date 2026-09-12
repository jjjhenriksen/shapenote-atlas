import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { matchesDiscovery, notationKind, resolveTuneLink, tuneUrl, recordKey, recordMode, availableParts, isTransposable } from '../src/discovery.js';
const corpus = JSON.parse(readFileSync(new URL('../public/corpus.json', import.meta.url)));
test('SH2025 filter partitions existing edition assets without promoting drafts', () => {
 const songs = corpus.songs.filter(s => s.books.includes('sh2025'));
 const counts = {};
 for (const s of songs) counts[notationKind(s, 'sh2025')] = (counts[notationKind(s, 'sh2025')] || 0) + 1;
 assert.deepEqual(counts, { reference: 487, exact: 13, draft: 90 });
 assert.equal(songs.filter(s => matchesDiscovery(s, 'sh2025', 'all', true)).length, 113);
 assert.equal(songs.filter(s => matchesDiscovery(s, 'sh2025', 'draft', true)).length, 87);
});
test('links round-trip Unicode IDs, preserve deployment path and native shell flag', () => {
 const song = corpus.songs.find(s => s.books.includes('sh2025'));
 const href = tuneUrl('http://localhost:5173/atlas/?nativeShell=1', 'sh2025', song.id);
 assert.equal(new URL(href).pathname, '/atlas/');
 assert.equal(new URL(href).searchParams.get('nativeShell'), '1');
 assert.deepEqual(resolveTuneLink(href, corpus), {bookId:'sh2025',songId:song.id});
});
test('invalid edition and mismatched tune links are explicit errors', () => {
 assert.equal(resolveTuneLink('http://localhost/', corpus), null);
 assert.ok(resolveTuneLink('http://localhost/?book=unknown&tune=1', corpus).error);
 const song = corpus.songs.find(s => !s.books.includes('sh2025'));
 assert.ok(resolveTuneLink(tuneUrl('http://localhost/', 'sh2025', song.id), corpus).error);
});
test('all eleven books partition completely and preserve their score mapping counts', () => {
 assert.equal(Object.keys(corpus.books).length, 11);
 for (const book of Object.keys(corpus.books)) {
  const songs = corpus.songs.filter(s => s.books.includes(book));
  const groups = ['exact','reference','draft','source-only'].map(kind => songs.filter(s => matchesDiscovery(s,book,kind,false)));
  assert.equal(groups.reduce((total, group) => total + group.length, 0), songs.length, book);
  assert.equal(groups[0].length, corpus.coverage.byBook[book].localScoreRecords, book);
  if (book !== 'sh2025') assert.equal(songs.filter(s => matchesDiscovery(s,book,'all',true)).length,0,book);
 }
});
test('discovery facets stay source-safe and use record-declared parts', () => {
 const songs = corpus.songs.filter(s => s.books.includes('sh1991'));
 const keyed = songs.find(s => s.metadataByBook?.sh1991?.keySignature);
 assert.ok(keyed);
 assert.equal(recordMode(keyed, 'sh1991'), 'major');
 assert.ok(matchesDiscovery(keyed, 'sh1991', 'all', false, { mode: 'major' }));
 assert.ok(!matchesDiscovery(keyed, 'sh1991', 'all', false, { mode: 'minor' }));
 const scored = songs.find(s => Array.isArray(s.scoreByBook?.sh1991?.parts) && s.scoreByBook.sh1991.parts.length);
 assert.ok(scored);
 const part = scored.scoreByBook.sh1991.parts[0].name;
 assert.ok(availableParts(scored, 'sh1991').includes(part.toLowerCase()));
 assert.ok(matchesDiscovery(scored, 'sh1991', 'all', false, { part }));
 assert.equal(isTransposable(scored, 'sh1991'), true);
});

test('unknown-key published drafts require manual input and are not transposable filter matches', () => {
 for (const [book, id] of [
  ['kentucky', 'kentucky 10 — New-Salem'],
  ['shenandoah', 'shenandoah 10 — Something New'],
 ]) {
  const song = corpus.songs.find(s => s.id === id);
  assert.ok(song, id);
  const draft = song.draftScoreByBook[book];
  assert.equal(draft.keyEvidence.status, 'unknown', id);
  assert.equal(draft.transposition.manualKeyAllowed, true, id);
  assert.equal(notationKind(song, book), 'draft', id);
  assert.equal(isTransposable(song, book), false, id);
  assert.equal(matchesDiscovery(song, book, 'draft', false, { transposable: true }), false, id);
  assert.equal(matchesDiscovery(song, book, 'draft'), true, id);
 }
});

test('validated exact and reference witnesses remain transposable without changing their classification', () => {
 const song = corpus.songs.find(s => s.id === 'sh 564 — Zion');
 assert.ok(song);
 for (const [book, kind, field] of [
  ['sh1991', 'exact', 'scoreByBook'],
  ['sh2025', 'reference', 'referenceScoreByBook'],
 ]) {
  const score = song[field][book];
  assert.equal(score.keyEvidence.status, 'source-verified', book);
  assert.equal(score.transposition.available, true, book);
  assert.ok(score.parts.every(part => part.events.length === 0), 'preview does not contain full pitched events');
  assert.equal(notationKind(song, book), kind, book);
  assert.equal(matchesDiscovery(song, book, kind, false, { transposable: true }), true, book);
 }
});

test('quarantined draft stays excluded even when it has an observed source key', () => {
 const song = corpus.songs.find(s => s.id === 'sh 453 (sh2025) — Newbury');
 assert.ok(song);
 const draft = song.draftScoreByBook.sh2025;
 assert.equal(draft.keyEvidence.status, 'source-observed');
 assert.ok(draft.keySignature);
 assert.equal(draft.playbackValidation.status, 'quarantined');
 assert.equal(isTransposable(song, 'sh2025'), false);
 assert.equal(matchesDiscovery(song, 'sh2025', 'draft'), true);
 for (const validation of [{ status: 'quarantined' }, { safeToApply: false }]) {
  const stale = { draftScoreByBook: { sh2025: { ...draft, transposition: { ...draft.transposition, available: true }, playbackValidation: validation } } };
  assert.equal(isTransposable(stale, 'sh2025'), false);
 }
});

test('transposable filter does not infer capability from keys, evidence, metadata, or other assets', () => {
 for (const capability of [undefined, { available: false }, { available: 'true' }, { manualKeyAllowed: true }]) {
  const witness = { keySignature: 'G major', keyEvidence: { status: 'source-verified' }, transposition: capability };
  const song = {
   referenceScoreByBook: { sh2025: witness },
   draftScoreByBook: { sh2025: { transposition: { available: true } } },
   scoreByBook: { sh1991: { transposition: { available: true } } },
   metadataByBook: { sh2025: { keySignature: 'A minor', keyEvidence: { status: 'source-verified' } } },
  };
  assert.equal(isTransposable(song, 'sh2025'), false);
 }
 assert.equal(isTransposable({ metadataByBook: { sh2025: { keySignature: 'A minor' } } }, 'sh2025'), false);
});

test('key facets normalize explicit fifths and distinguish accidental spellings', () => {
 const song = keySignature => ({ scoreByBook: { sh1991: { keySignature } } });
 for (const [encoded, named] of [['-4:major', 'Ab major'], ['0:minor', 'A minor'], ['3:minor', 'F# minor'], ['Bb:major', 'Bb major']]) {
  assert.equal(recordKey(song(encoded), 'sh1991'), named);
  assert.ok(matchesDiscovery(song(encoded), 'sh1991', 'all', false, { key: named.split(' ')[0] }));
 }
 for (const [key, other] of [['F', 'F#'], ['B', 'Bb'], ['C', 'Cb']]) {
  assert.equal(matchesDiscovery(song(`${other} major`), 'sh1991', 'all', false, { key }), false);
 }
 for (const key of ['C', '0', '1:unknown', '2:dorian', '8:major']) {
  assert.equal(recordKey(song(key), 'sh1991'), '');
  assert.equal(recordMode(song(key), 'sh1991'), 'unknown');
 }
});
