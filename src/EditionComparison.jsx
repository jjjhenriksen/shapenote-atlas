import React from 'react';
import { editionComparisons } from './editionComparison.js';

export function EditionComparison({ song, corpus, bookId }) {
  const editions = editionComparisons(song, corpus, window.location.href);
  if (editions.length < 2) return null;
  return <details className="edition-comparison">
    <summary>Compare editions</summary>
    <p>{song.editionReconciliation.status === 'change-flagged'
      ? 'The reconciliation register flags an edition change.'
      : 'No change is listed in the reconciliation register. This does not establish identical text or music.'}
      {' '}Catalogue relationships do not certify source fidelity.</p>
    <ul>{editions.map((edition) => <li key={edition.bookId}>
      <strong>{edition.label}{edition.bookId === bookId ? ' (selected)' : ''}</strong>
      <p>{edition.record?.songNo} — {edition.record?.title}<br />{edition.availability}</p>
      <div className="source-actions">
        {edition.href && edition.bookId !== bookId && <a href={edition.href}>Open {edition.label} record</a>}
        {edition.record?.url && <a href={edition.record.url} target="_blank" rel="noreferrer noopener">Open {edition.label} source</a>}
      </div>
    </li>)}</ul>
  </details>;
}
