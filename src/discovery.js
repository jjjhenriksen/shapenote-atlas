// Availability describes the selected edition's existing asset, never a promotion.
export function notationKind(song, bookId) {
  if (song.scoreByBook?.[bookId]) return 'exact';
  if (song.referenceScoreByBook?.[bookId]) return 'reference';
  if (song.draftScoreByBook?.[bookId]) return 'draft';
  return 'source-only';
}

export function recordKey(song, bookId) {
  const score = song.scoreByBook?.[bookId] || song.referenceScoreByBook?.[bookId] || song.draftScoreByBook?.[bookId] || {};
  return score.keySignature || song.metadataByBook?.[bookId]?.keySignature || '';
}

export function recordMode(song, bookId) {
  const key = recordKey(song, bookId);
  return String(key).includes(':') ? String(key).split(':').pop().toLowerCase() : /\b(minor)\b/i.test(key) ? 'minor' : key ? 'major' : 'unknown';
}

export function availableParts(song, bookId) {
  const score = song.scoreByBook?.[bookId] || song.referenceScoreByBook?.[bookId] || song.draftScoreByBook?.[bookId];
  return Array.isArray(score?.parts) ? score.parts.map((part) => String(part.name || '').toLowerCase()).filter(Boolean) : [];
}

export function isTransposable(song, bookId) {
  const score = song.scoreByBook?.[bookId] || song.referenceScoreByBook?.[bookId] || song.draftScoreByBook?.[bookId];
  return Boolean(score?.transposition?.available || score?.keySignature || score?.keyEvidence);
}

export function matchesDiscovery(song, bookId, availability = 'all', additionsOnly = false, facets = {}) {
  return (availability === 'all' || notationKind(song, bookId) === availability)
    && (!additionsOnly || song.metadataByBook?.[bookId]?.editionStatus === 'added-in-2025'
      || song.sourceCoverageByBook?.[bookId]?.editionStatus === 'added-in-2025')
    && (!facets.mode || recordMode(song, bookId) === facets.mode)
    && (!facets.key || recordKey(song, bookId).toLowerCase().startsWith(facets.key.toLowerCase()))
    && (!facets.transposable || isTransposable(song, bookId))
    && (!facets.part || availableParts(song, bookId).includes(facets.part.toLowerCase()));
}

export function tuneUrl(href, bookId, songId) {
  const url = new URL(href);
  url.searchParams.set('book', bookId);
  url.searchParams.set('tune', songId);
  return url.href;
}

export function resolveTuneLink(href, corpus) {
  const params = new URL(href).searchParams;
  if (!params.has('book') && !params.has('tune')) return null;
  const bookId = params.get('book');
  const songId = params.get('tune');
  if (!corpus.books[bookId]) return { error: 'This tune link names an unknown book. Choose a book to continue.' };
  const song = corpus.songs.find((item) => item.id === songId && item.books.includes(bookId));
  if (!song) return { error: 'This tune link does not match a record in this edition. Search for the tune or choose another book.' };
  return { bookId, songId };
}
