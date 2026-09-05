import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { matchesDiscovery, notationKind, resolveTuneLink, tuneUrl, recordMode, availableParts, isTransposable } from '../src/discovery.js';
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
