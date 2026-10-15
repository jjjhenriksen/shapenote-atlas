import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, symlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { buildReaderData, CATALOGUE_BUDGET } from '../scripts/build_reader_data.mjs';
import { validateCorpus } from '../src/corpusContract.js';
import { notationKind, recordKey, availableParts, isTransposable, matchesDiscovery } from '../src/discovery.js';
const publicDir = new URL('../public/', import.meta.url);
const load = (name) => JSON.parse(readFileSync(new URL(name, publicDir)));

test('compact catalogue preserves every edition/facet, review gate, and full lazy evidence record within budget', () => {
  const directory = mkdtempSync(join(tmpdir(), 'atlas-reader-data-'));
  try {
    for (const name of ['corpus.json', 'human-review-queue.json', 'source-health.json']) symlinkSync(new URL(name, publicDir), join(directory, name));
    const result = buildReaderData(directory);
    const catalogue = JSON.parse(readFileSync(join(directory, 'reader-data/catalogue.json')));
    const corpus = load('corpus.json');
    const queue = load('human-review-queue.json');
    const health = load('source-health.json');
    validateCorpus(catalogue);
    assert.ok(result.catalogueBytes <= CATALOGUE_BUDGET);
    assert.equal(catalogue.songs.length, corpus.songs.length);
    assert.deepEqual(catalogue.books, corpus.books);
    assert.deepEqual(catalogue.coverage, corpus.coverage);
    assert.deepEqual(catalogue.reviewQueue.reviewNow, queue.reviewNow.map(({queueId,status}) => ({queueId,status})));
    for (const [index, original] of corpus.songs.entries()) {
      const compact = catalogue.songs[index];
      assert.equal(compact.id, original.id);
      assert.deepEqual(compact.books, original.books);
      for (const book of original.books) {
        for (const fn of [notationKind, recordKey, availableParts, isTransposable]) assert.deepEqual(fn(compact, book), fn(original, book), `${original.id}/${book}/${fn.name}`);
        for (const kind of ['all', 'exact', 'reference', 'draft', 'source-only', 'prose']) {
          assert.equal(matchesDiscovery(compact, book, kind, true), matchesDiscovery(original, book, kind, true));
        }
      }
      const body = readFileSync(join(directory, compact.detailRef));
      assert.ok(compact.detailRef.includes(createHash('sha256').update(body).digest('hex')));
      const detail = JSON.parse(body);
      assert.deepEqual(detail.song, original); // includes fields deliberately absent from search
      assert.deepEqual(detail.reviewQueue.reviewNow, original.books.flatMap((book) => queue.reviewNow.filter((item) => item.queueId === `${book}/${original.songNo}`)));
      const urls = new Set(original.urls || []);
      for (const metadata of Object.values(original.metadataByBook || {})) {
        if (metadata.sourceUrl) urls.add(metadata.sourceUrl);
        for (const url of metadata.sourceUrls || []) urls.add(url);
      }
      assert.deepEqual(detail.sourceHealth.records, [...urls].map((url) => health.records.find((item) => item.url === url)).filter(Boolean));
    }
  } finally { rmSync(directory, {recursive:true, force:true}); }
});
