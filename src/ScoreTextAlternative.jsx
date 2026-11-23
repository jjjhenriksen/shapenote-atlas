import React, { useMemo, useState } from 'react';
import { scoreText } from './scoreText.js';

export function ScoreTextAlternative({ score, sourceKey, targetKey, transpose, reviewDraft }) {
  const [open, setOpen] = useState(false);
  const text = useMemo(() => {
    if (!open) return null;
    try { return scoreText(score, { sourceKey, targetKey, transpose, reviewDraft }); }
    catch (error) { return { error: error.message }; }
  }, [open, score, sourceKey, targetKey, transpose, reviewDraft]);

  return <details className="score-text-alternative" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Read score as text</summary>
    {text?.error ? <p role="status">Score text unavailable: {text.error}</p> : text && <>
      <p>{text.transposed ? 'Displayed transposed pitches' : 'Recorded pitches'}, timing and encoded lyric text, in written order. Offsets are measured from each measure’s start in quarter-note beats. Simultaneous events keep their voice and staff labels. This text does not describe all engraving marks or expand repeats.</p>
      {text.suppressed > 0 && <p>{text.suppressed} ambiguous notes are omitted, matching the review engraving.</p>}
      {text.parts.map((part, partIndex) => <section key={partIndex}>
        <h3>{part.name}</h3>
        {part.measures.map((measure) => <section key={measure.number}>
          <h4>Measure {measure.number}</h4>
          {measure.events.length ? <ol>{measure.events.map((event) => <li key={event.index}>{event.text}</li>)}</ol> : <p>No encoded notes or rests in this measure.</p>}
        </section>)}
      </section>)}
    </>}
  </details>;
}
