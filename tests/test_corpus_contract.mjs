import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateCorpus } from '../src/corpusContract.js';
const valid = () => ({ books: { sh1991: { label: 'Sacred Harp 1991' } }, songs: [{ id: 'a', title: 'Tune', songNo: '1', books: ['sh1991'] }] });

test('committed corpus passes without changing source data', () => {
  const data = JSON.parse(readFileSync(new URL('../public/corpus.json', import.meta.url)));
  assert.equal(validateCorpus(data), data);
  assert.ok(data.songs.length > 0);
});
for (const [name, payload] of Object.entries({ null: null, missing: {}, songsMissing: { books: valid().books }, songsObject: { ...valid(), songs: {} }, songsNull: { ...valid(), songs: null }, booksMissing: { songs: [] }, booksArray: { ...valid(), books: [] }, booksNull: { ...valid(), books: null }, booksEmpty: { ...valid(), books: {} } })) {
  test(`rejects valid JSON with ${name} collections`, () => assert.throws(() => validateCorpus(payload), /Incompatible corpus/));
}
test('minimal metadata-only and empty catalogues are valid', () => {
  assert.equal(validateCorpus(valid()).songs.length, 1);
  assert.deepEqual(validateCorpus({ ...valid(), songs: [] }).songs, []);
});
for (const [name, change] of Object.entries({ membership: (s) => s.books = {}, missingBook: (s) => s.books = ['unknown'], title: (s) => s.title = {}, urls: (s) => s.urls = 'url', metadataSources: (s) => s.metadataByBook = { sh1991: { sourceUrls: {} } }, scoreParts: (s) => s.scoreByBook = { sh1991: { parts: {} } }, partEvents: (s) => s.scoreByBook = { sh1991: { parts: [{ name: 'Tenor', events: {} }] } } })) {
  test(`rejects malformed nested ${name}`, () => { const data = valid(); change(data.songs[0]); assert.throws(() => validateCorpus(data), /Incompatible corpus/); });
}
