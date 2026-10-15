import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const DETAIL_BUDGET = 1_000_000;
export const CATALOGUE_BUDGET = 4_000_000; // decoded UTF-8 bytes, independent of host compression
const pick = (object, keys) => Object.fromEntries(keys.filter((key) => Object.hasOwn(object, key)).map((key) => [key, object[key]]));
const mapValues = (object, project) => Object.fromEntries(Object.entries(object || {}).map(([key, value]) => [key, project(value)]));

export function catalogueSong(song) {
  const record = pick(song, ['id', 'songNo', 'title', 'books', 'rawFirstLine', 'textKey', 'urls']);
  record.metadataByBook = mapValues(song.metadataByBook, (value) => pick(value, ['composer', 'lyricist', 'keySignature', 'editionStatus', 'sourceUrl', 'sourceUrls']));
  record.sourceCoverageByBook = mapValues(song.sourceCoverageByBook, (value) => pick(value, ['status', 'contentKind', 'nextAction', 'editionStatus', 'sourceUrls', 'editionEvidenceUrl', 'sourceImageUrl']));
  for (const key of ['scoreByBook', 'referenceScoreByBook', 'draftScoreByBook']) {
    if (!song[key]) continue;
    record[key] = mapValues(song[key], (score) => ({
      ...pick(score, ['keySignature', 'transposition', 'playbackValidation']),
      parts: (score.parts || []).map((part) => ({ name: part.name })),
    }));
  }
  return record;
}

export function buildReaderData(publicDir) {
  const load = (name) => JSON.parse(readFileSync(resolve(publicDir, name), 'utf8'));
  const corpus = load('corpus.json');
  const queue = load('human-review-queue.json');
  const health = load('source-health.json');
  const healthByUrl = new Map(health.records.map((record) => [record.url, record]));
  const queueById = new Map();
  for (const item of queue.reviewNow) {
    if (!queueById.has(item.queueId)) queueById.set(item.queueId, []);
    queueById.get(item.queueId).push(item); // duplicates must remain ambiguous
  }
  const directory = resolve(publicDir, 'reader-data');
  mkdirSync(directory, { recursive: true });
  const songs = corpus.songs.map((song) => {
    const urls = new Set(song.urls || []);
    for (const metadata of Object.values(song.metadataByBook || {})) {
      if (metadata.sourceUrl) urls.add(metadata.sourceUrl);
      for (const url of metadata.sourceUrls || []) urls.add(url);
    }
    const detail = {
      song, // lossless original record, including all edition-scoped provenance
      reviewQueue: { reviewNow: song.books.flatMap((id) => queueById.get(`${id}/${song.songNo}`) || []) },
      sourceHealth: { generatedAt: health.generatedAt, records: [...urls].map((url) => healthByUrl.get(url)).filter(Boolean) },
    };
    const body = JSON.stringify(detail);
    if (Buffer.byteLength(body) > DETAIL_BUDGET) throw new Error(`Tune detail exceeds decoded budget ${DETAIL_BUDGET}: ${song.id}`);
    const hash = createHash('sha256').update(body).digest('hex');
    const name = `${hash}.json`; // content addressing prevents mixed catalogue/detail generations
    writeFileSync(resolve(directory, name), body);
    return { ...catalogueSong(song), detailRef: `/reader-data/${name}` };
  });
  const catalogue = {
    readerDataVersion: 1, ...pick(corpus, ['generatedAt', 'source', 'books', 'coverage']), songs,
    reviewQueue: { reviewNow: queue.reviewNow.map((item) => pick(item, ['queueId', 'status'])) },
  };
  const body = JSON.stringify(catalogue);
  const bytes = Buffer.byteLength(body);
  if (bytes > CATALOGUE_BUDGET) throw new Error(`Reader catalogue ${bytes} exceeds decoded budget ${CATALOGUE_BUDGET}`);
  writeFileSync(resolve(directory, 'catalogue.json'), body);
  return { songs: songs.length, catalogueBytes: bytes, catalogueBudget: CATALOGUE_BUDGET };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(JSON.stringify(buildReaderData(resolve(process.env.ATLAS_PUBLIC_DIR || 'public'))));
}
