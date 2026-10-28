import { notationKind, tuneUrl } from './discovery.js';

const LABELS = {
  exact: 'Catalogued score — source fidelity still requires review',
  reference: 'Alternate-edition reference only',
  draft: 'Review draft only',
  'source-only': 'No structured score attached',
  prose: 'Prose article',
};

// Join only on the explicit reconciliation identity, never a similar title.
// Ambiguous mappings stay unavailable instead of choosing the first match.
export function editionComparisons(song, corpus, href) {
  const relation = song?.editionReconciliation;
  if (!relation?.relationId || !Array.isArray(relation.books)) return [];
  return relation.books.map((bookId) => {
    const matches = corpus.songs.filter((candidate) => candidate.books.includes(bookId)
      && (candidate.editionRelationId || candidate.editionReconciliation?.relationId) === relation.relationId);
    const target = matches.length === 1 ? matches[0] : null;
    return {
      bookId,
      label: corpus.books[bookId]?.label || bookId,
      record: relation.records?.[bookId],
      availability: target ? LABELS[notationKind(target, bookId)] : 'Catalogue relationship unavailable or ambiguous',
      href: target ? tuneUrl(href, bookId, target.id) : null,
    };
  });
}
