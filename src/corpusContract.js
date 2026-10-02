const record = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value) => typeof value === 'string';
function requireValue(condition, path) {
  if (!condition) throw new Error(`Incompatible corpus bundle: ${path}`);
}
function optionalArray(value, path, validItem = () => true) {
  if (value == null) return;
  requireValue(Array.isArray(value) && value.every(validItem), path);
}
function sourceCollections(value, path) {
  requireValue(record(value), path);
  for (const key of ['sourceUrls', 'recordingSourcePages']) optionalArray(value[key], `${path}.${key}`, text);
  optionalArray(value.recordingTracks, `${path}.recordingTracks`, (track) => record(track) && text(track.title) && text(track.url));
  optionalArray(value.cleanSourceCandidates, `${path}.cleanSourceCandidates`, record);
}

// Validate the collections used by the reader, without inferring musical
// semantics or requiring optional provenance/notation for metadata-only songs.
export function validateCorpus(data, supportedBooks) {
  requireValue(record(data), 'root must be an object');
  requireValue(record(data.books), 'books must be a keyed object');
  requireValue(Object.keys(data.books).length > 0, 'books must not be empty');
  if (supportedBooks) requireValue(supportedBooks.some((id) => data.books[id]), 'no supported book');
  for (const [id, book] of Object.entries(data.books)) requireValue(record(book) && text(book.label) && book.label.length > 0, `books.${id}.label`);
  requireValue(Array.isArray(data.songs), 'songs must be an array');
  const ids = new Set();
  data.songs.forEach((song, index) => {
    const path = `songs[${index}]`;
    requireValue(record(song), path);
    for (const key of ['id', 'title', 'songNo']) requireValue(text(song[key]) && song[key].length > 0, `${path}.${key}`);
    requireValue(!ids.has(song.id), `${path}.id must be unique`); ids.add(song.id);
    requireValue(Array.isArray(song.books) && song.books.length > 0 && song.books.every((id) => text(id) && Object.hasOwn(data.books, id)), `${path}.books`);
    optionalArray(song.urls, `${path}.urls`, text);
    for (const key of ['rawFirstLine', 'textKey']) if (song[key] != null) requireValue(text(song[key]), `${path}.${key}`);
    for (const key of ['metadata', 'sourceCoverage']) if (song[key] != null) sourceCollections(song[key], `${path}.${key}`);
    for (const key of ['metadataByBook', 'sourceCoverageByBook', 'scoreByBook', 'referenceScoreByBook', 'draftScoreByBook']) {
      if (song[key] == null) continue;
      requireValue(record(song[key]), `${path}.${key}`);
      for (const [id, value] of Object.entries(song[key])) {
        if (value == null) continue;
        requireValue(record(value), `${path}.${key}.${id}`);
        if (key.endsWith('ScoreByBook') || key === 'scoreByBook') {
          for (const field of ['sourceUrl', 'scoreRef', 'keySignature']) if (value[field] != null) requireValue(text(value[field]), `${path}.${key}.${id}.${field}`);
          requireValue(Array.isArray(value.parts), `${path}.${key}.${id}.parts`);
          value.parts.forEach((part) => {
            requireValue(record(part) && text(part.name) && part.name.length > 0, `${path}.${key}.${id}.part`);
            for (const collection of ['events', 'lyrics', 'barlines']) optionalArray(part[collection], `${path}.${key}.${id}.${collection}`, record);
          });
        } else sourceCollections(value, `${path}.${key}.${id}`);
      }
    }
  });
  return data;
}
