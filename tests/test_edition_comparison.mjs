import { test } from 'node:test';
import assert from 'node:assert/strict';
import { editionComparisons } from '../src/editionComparison.js';
import { catalogueSong } from '../scripts/build_reader_data.mjs';
import { readFileSync } from 'node:fs';
const corpus = JSON.parse(readFileSync(new URL('../public/corpus.json', import.meta.url)));
const compact = { ...corpus, songs: corpus.songs.map(catalogueSong) };

test('explicit relationship resolves separate Ester records and selected-edition availability', () => {
  const song = corpus.songs.find(s => s.id === 'sh 37t (sh1991) — Ester');
  const rows = editionComparisons(song, compact, 'https://example.org/atlas/?book=sh1991');
  assert.equal(rows.length, 2);
  const target = new URL(rows[1].href);
  assert.equal(target.pathname, '/atlas/');
  assert.equal(target.searchParams.get('book'), 'sh2025');
  assert.equal(target.searchParams.get('tune'), 'sh 37t (sh2025) — Ester');
  assert.notEqual(rows[1].availability, rows[0].availability);
});

test('shared records retain identity without borrowing an exact score', () => {
  const song = corpus.songs.find(s => s.id === 'sh 26 — Samaria');
  const rows = editionComparisons(song, compact, 'https://example.org/');
  assert.equal(new URL(rows[1].href).searchParams.get('tune'), song.id);
  assert.equal(rows[1].availability, 'Alternate-edition reference only');
});

test('missing and ambiguous relations never fall back to title matches', () => {
  const song = corpus.songs.find(s => s.id === 'sh 26 — Samaria');
  assert.equal(editionComparisons(song, { ...compact, songs: [] }, 'https://example.org/')[0].href, null);
  const target = compact.songs.find(s => s.id === song.id);
  assert.equal(editionComparisons(song, { ...compact, songs: [target, target] }, 'https://example.org/')[0].href, null);
  assert.deepEqual(editionComparisons({}, compact, 'https://example.org/'), []);
});
