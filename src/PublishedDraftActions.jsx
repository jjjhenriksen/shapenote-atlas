import React from "react";
import { WitnessFileAction } from "./WitnessFileAction.jsx";

export function PublishedDraftActions({ draft, song, bookLabel, assetUrl }) {
  const publication = draft?.reviewPublication;
  if (!publication) return null;
  const title = `${bookLabel} / ${song.songNo} ${song.title} — correction`;
  const body = [
    `Draft: ${publication.version}`,
    `Tune: ${bookLabel} / ${song.songNo} ${song.title}`,
    "",
    "Voice and measure:",
    "Current notation or lyric:",
    "Suggested correction:",
    "Source page / evidence:",
    "",
    "Attach corrected MusicXML if available.",
  ].join("\n");
  const correctionUrl = `https://github.com/jjjhenriksen/shapenote-atlas/issues/new?${new URLSearchParams({ title, body })}`;
  return <section className="shape-review-draft-panel published-draft-actions" aria-label="Correct this draft">
    <h3>Use it now. Help improve it.</h3>
    <p>{publication.completeness === "partial" ? "This draft stops before the end of the tune. " : ""}Download the editable score, compare it with the source, and report a correction. You can edit MusicXML in a notation editor such as MuseScore; submitting a correction opens GitHub for your review.</p>
    <div className="shape-review-draft-actions">
      <WitnessFileAction url={publication.musicXmlUrl} label="editable MusicXML" assetUrl={assetUrl} description={`Correction draft ${publication.version}; original file, without display transposition`} />
      {publication.originalMusicXmlUrl && <WitnessFileAction url={publication.originalMusicXmlUrl} label="original witness" assetUrl={assetUrl} />}
      {publication.sourceUrl && <a href={assetUrl(publication.sourceUrl)} target="_blank" rel="noreferrer noopener">{publication.sourcePublicationPolicy === "external-link-only" ? "Open source PDF" : "Compare source"}</a>}
      <a href={correctionUrl} target="_blank" rel="noreferrer noopener">Suggest a correction on GitHub</a>
      {publication.evidenceUrl && <a href={assetUrl(publication.evidenceUrl)} target="_blank" rel="noreferrer noopener">Review notes</a>}
    </div>
    {publication.limitations?.length > 0 && <details><summary>Known gaps in {publication.version}</summary><ul>{publication.limitations.map((gap) => <li key={gap}>{gap}</li>)}</ul></details>}
  </section>;
}
