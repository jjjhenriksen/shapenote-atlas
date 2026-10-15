import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { matchesDiscovery, recordKey, resolveTuneLink, tuneUrl } from "./discovery.js";
import { scoreSemanticSummary } from "./agent_11_score_semantics.js";
import { buildPracticeSchedule, canApplyPlaybackPlan, resolveRepeatPlayback, guardedAudioAction, resolvePlaybackQuarantine, sessionIsCurrent, shouldCompleteSession } from "./practice.js";
import { createAudioState, stopAudioResources, disposeAudio, schedulePracticeAudio } from "./audioPlayback.js";
import { CLEF_GLYPH } from "./clefNotation.js";
import { ScoreEngraving } from "./ScoreEngraving.jsx";
import { scoreMeasures, shapeForScoreEvent } from "./scoreMusicXml.js";
import { validateCorpus } from "./corpusContract.js";
import { summarizeSourceHealth } from "./sourceHealthPresentation.js";
import { resolveKeyContext } from "./keyResolution.js";
import { PublishedDraftActions } from "./PublishedDraftActions.jsx";
import { parseKey, pitchToMidi, ROOT_PITCH } from "./notation.js";

const PUBLIC_BASE = import.meta.env.BASE_URL || "/";

function assetUrl(path) {
  if (!path || /^(?:https?:|data:|#)/i.test(String(path))) return path;
  return `${PUBLIC_BASE}${String(path).replace(/^\/+/, "")}`;
}

const BOOK_ORDER = ["sh1991", "sh2025", "shcooper2012", "ch7", "shenandoah", "southernharmony", "kentucky", "socialharp", "mnharmony", "sacredharptunes", "trumpet"];
const KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];

function Icon({ name, size = 18 }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true" };
  const paths = {
    book: <><path d="M4 5.5c0-1 1-1.5 2-1.5h5v16H6c-1.1 0-2-.9-2-2z" /><path d="M20 5.5c0-1-1-1.5-2-1.5h-5v16h5c1.1 0 2-.9 2-2z" /><path d="M7 7h2M15 7h2" /></>,
    practice: <><path d="M9 18V6" /><path d="M9 6l9-2v12" /><ellipse cx="6" cy="18" rx="3" ry="2.2" /><ellipse cx="16" cy="16" rx="3" ry="2.2" /></>,
    source: <><path d="M6 3.5h9l3 3V20a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z" /><path d="M14 3.5V7h4M8 11h8M8 15h8M8 18h5" /></>,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
    play: <path d="m8 5 11 7-11 7z" fill="currentColor" stroke="none" />,
    pause: <><path d="M8 5v14M16 5v14" strokeWidth="2.2" /></>,
    stop: <rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor" stroke="none" />,
    arrowDown: <><path d="M12 4v15M6 13l6 6 6-6" /></>,
    arrowUp: <><path d="M12 20V5M6 11l6-6 6 6" /></>,
    download: <><path d="M12 4v11M7 11l5 5 5-5" /><path d="M5 20h14" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 10v6M12 7.5h.01" strokeWidth="2.2" /></>,
    external: <><path d="M14 5h5v5M19 5l-8 8" /><path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
    chevron: <path d="m9 6 6 6-6 6" />,
  };
  return <svg {...common}>{paths[name]}</svg>;
}

function normalize(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function getBookSongs(data, bookId) {
  return (data?.songs || []).filter((song) => song.books.includes(bookId));
}

function rootFromKey(key) {
  return parseKey(key)?.rootPitch ?? 0;
}

function keyMode(key) {
  return parseKey(key)?.mode || "";
}

function keyLabel(key) {
  const parsed = parseKey(key);
  return parsed ? `${parsed.rootName} ${parsed.mode}` : "Key unavailable";
}


function getBookMetadata(song, bookId) {
  return song?.metadataByBook?.[bookId] || null;
}

function getBookScore(song, bookId) {
  return song?.scoreByBook?.[bookId] || null;
}

function getBookReferenceScore(song, bookId) {
  return song?.referenceScoreByBook?.[bookId] || null;
}

function getBookDraftScore(song, bookId) {
  return song?.draftScoreByBook?.[bookId] || null;
}

function coverageLabel(coverage) {
  if (!coverage) return "Coverage not recorded";
  return {
    "structured-score": "Structured score",
    "source-reference": "Source reference",
    "transcription-blocked": "Transcription blocked",
    "metadata-only": "Metadata only",
    "mapping-gap": "Source mapping gap",
    "non-notation": "Prose article",
  }[coverage.status] || "Coverage recorded";
}

function coverageNextStep(coverage) {
  if (!coverage) return "Review the source record before adding notation.";
  return {
    "structured-score": "Verify source fidelity and playback.",
    "source-reference": "Transcribe and verify from the recorded source.",
    "transcription-blocked": "Acquire a clean authorized source before transcribing.",
    "metadata-only": "Acquire an authorized source before transcribing.",
    "mapping-gap": "Repair the edition-to-source mapping before transcribing.",
    "non-notation": "Preserved as a catalogue reference; no notation transcription is required.",
  }[coverage.status] || "Review the source record before adding notation.";
}

function isSourceRecord(song, bookId) {
  const status = song?.sourceCoverageByBook?.[bookId]?.status;
  return Boolean(status && status !== "structured-score");
}

function sourceRowStatus(song, bookId) {
  const status = song?.sourceCoverageByBook?.[bookId]?.status;
  return {
    "source-reference": { label: "source", icon: "check" },
    "transcription-blocked": { label: "blocked", icon: "info" },
    "metadata-only": { label: "metadata", icon: "info" },
    "mapping-gap": { label: "mapping gap", icon: "info" },
    "non-notation": { label: "article", icon: "info" },
  }[status] || { label: "source", icon: "info" };
}

function getExplicitSourceKey(song, bookId) {
  return getBookScore(song, bookId)?.keySignature || getBookMetadata(song, bookId)?.keySignature || "";
}

function shapeSourcePdfUrl(score) {
  const sourceUrl = score?.sourceUrl || "";
  if (!sourceUrl.includes("shapenote.net/musicxml/")) return "";
  return sourceUrl.replace("/musicxml/", "/pdf/").replace(/\.mxl(?:[?#].*)?$/i, ".pdf");
}

function shapeKeyForSong(song, bookId) {
  return getExplicitSourceKey(song, bookId);
}

function keyEvidenceFor(record, fallback = null) {
  if (record?.keyEvidence) return record.keyEvidence;
  if (record?.keySignature && record?.provenance?.kind === "omr-draft") {
    return record.provenance.sourceKeyVerified === false
      ? { status: "omr-detected", source: "OMR-detected MusicXML key signature" }
      : { status: "source-verified", source: "source metadata" };
  }
  if (record?.keySignature) return { status: "source-verified", source: "structured/source metadata" };
  return fallback || { status: "unknown", source: "not recorded" };
}

function keyEvidenceLabel(evidence, keyName, reference = false) {
  if (!keyName || evidence?.status === "unknown") return "Key unavailable";
  if (evidence?.status === "omr-detected") return `OMR-detected key: ${keyName}`;
  if (evidence?.status === "source-observed") return `Source-observed key: ${keyName}`;
  if (evidence?.status === "entered") return `Entered source key: ${keyName}`;
  return `${reference ? "Source-verified witness key" : "Source-verified key"}: ${keyName}`;
}

function isRejectedReviewItem(item) {
  return item?.status === "rejected" || item?.status === "rejected-source-mismatch";
}

function reviewDisposition(item, ambiguous = false) {
  if (ambiguous) {
    return {
      label: "Ambiguous evidence",
      badge: "Ambiguous",
      badgeClass: "ambiguous-evidence",
      heading: "Multiple evidence records need reconciliation",
      summary: "More than one review record is attached to this tune, so the dashboard will not treat its draft as promotion-safe.",
    };
  }
  const status = item?.status || "";
  if (isRejectedReviewItem(item)) {
    return {
      label: "Rejected source mismatch",
      badge: "Rejected",
      badgeClass: "rejected-source-mismatch",
      heading: "Candidate rejected for source mismatch",
      summary: "Autonomous comparison found that the retained candidate does not establish this edition’s tune.",
    };
  }
  if (status === "autonomously-blocked") {
    return {
      label: "Autonomously blocked",
      badge: "Blocked",
      badgeClass: "autonomously-blocked",
      heading: "Transcription blocked by source evidence",
      summary: "Autonomous comparison found unresolved source evidence, so this draft remains isolated and is not promoted.",
    };
  }
  return {
    label: "Review only",
    badge: "Review only",
    badgeClass: "review-only",
    heading: "Four-shape MusicXML is ready for review",
    summary: "This draft is downloadable for checking against the untouched page, but it is not authoritative notation.",
  };
}

function reviewQueueItems(queue, song, bookId) {
  return (queue?.reviewNow || []).filter((item) => item.queueId === `${bookId}/${song?.songNo || ""}`);
}

function reviewQueueItem(queue, song, bookId) {
  return reviewQueueItems(queue, song, bookId)[0];
}

function reviewQueueIsAmbiguous(queue, song, bookId) {
  return reviewQueueItems(queue, song, bookId).length > 1;
}

function partStaff(part, partIndex) {
  const declaredClefs = Object.values(part?.clefs || {});
  const eventClef = (part?.events || []).find((event) => event.clef)?.clef;
  const clef = eventClef || declaredClefs[0] || "";
  if (clef === "bass" || clef === "tenor" || clef === "alto" || clef === "treble") return clef;
  return partIndex < 2 ? "treble" : "bass";
}

function partClefGlyph(part, partIndex) {
  return CLEF_GLYPH[partStaff(part, partIndex)];
}



function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function ShapeLegend() {
  return <div className="shape-legend" role="group" aria-label="Four-shape solfege reference">
    <span><i className="shape shape-fa" />fa</span>
    <span><i className="shape shape-sol" />sol</span>
    <span><i className="shape shape-la" />la</span>
    <span><i className="shape shape-mi" />mi</span>
  </div>;
}

function sourcePdfUrl(song) {
  return (song?.urls || []).find((url) => /\.pdf(?:$|[?#])/i.test(url)) || "";
}

function sourceHostLabel(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "linked page";
  }
}

function healthStatusLabel(record) {
  if (record?.retentionStatus === "local-drift") return "retention drift";
  if (record?.status === "not-checked-budget" || record?.status === "budget") return "budget-excluded";
  if (record?.status === "offline") return "offline";
  if (record?.status === "cached" && record?.networkStatus === "network-error") return "network-error cache";
  if (record?.status === "reachable" || record?.status === "current") return "current";
  if (record?.status === "cached") return "cached";
  return record?.status || "unknown";
}

function sourceDestinationLabel(url) {
  try {
    const parsed = new URL(url);
    const path = `${parsed.pathname}${parsed.search}` || "/";
    return `${parsed.hostname.replace(/^www\./, "")}${path}`;
  } catch {
    return sourceHostLabel(url);
  }
}

function shenandoahImageUrl(song) {
  if (!song?.songNo || !song?.title) return "";
  const match = String(song.songNo).match(/^(\d+)([tb])?$/i);
  if (!match) return "";
  const number = Number(match[1]);
  const suffix = (match[2] || "").toLowerCase();
  const lower = number < 100 ? 1 : Math.floor(number / 100) * 100;
  const upper = Math.min(number < 100 ? 99 : lower + 99, 457);
  const pad = (value) => String(value).padStart(3, "0");
  const safeTitle = String(song.title).replace(/[’']/g, "").replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const stem = `${match[1]}${suffix}-${safeTitle}`;
  return `https://shenandoah.harmony.sacredharpbremen.org/wp-content/uploads/Songs/${pad(lower)}-${pad(upper)}/${pad(number)}${suffix}-${safeTitle}/${encodeURIComponent(stem)}.jpg`;
}

function sourcePageUrl(song, bookId) {
  if (!['shenandoah', 'sacredharptunes'].includes(bookId)) return "";
  return (song?.urls || []).find((url) => !/\.pdf(?:$|[?#])/i.test(url)) || "";
}

function SourceNotation({ song, bookId }) {
  const prose = song.sourceCoverageByBook?.[bookId]?.contentKind === "prose";
  const pdfUrl = prose ? song.sourceIdentityReview?.sourceUrl : sourcePdfUrl(song);
  const imageUrl = bookId === "shenandoah"
    ? shenandoahImageUrl(song)
    : bookId === "sh2025"
      ? song?.metadataByBook?.[bookId]?.sourceImageUrl || ""
      : "";
  const pageUrl = sourcePageUrl(song, bookId) || (bookId === "sh2025"
    ? song?.metadataByBook?.[bookId]?.sourceUrl || (song?.urls || []).find((url) => /sacredharpbremen\.org\//.test(url) || /fasola\.org\/indexes\/2025/.test(url)) || ""
    : "");
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => setImageFailed(false), [song?.id, imageUrl]);
  if (!pdfUrl && !imageUrl && !pageUrl) return null;
  if (imageUrl && !imageFailed) return <div className="source-notation" data-image-url={imageUrl}><div className="source-notation-head"><span className="section-label">Source scan</span><span>Page image · not transposable</span></div><img src={imageUrl} alt={`${song.songNo} ${song.title} source notation`} loading="lazy" referrerPolicy="no-referrer" onError={() => setImageFailed(true)} /><a href={pageUrl || imageUrl} target="_blank" rel="noreferrer noopener">Open the authoritative source page <Icon name="external" size={16} /></a></div>;
  if (pdfUrl && !imageUrl) return <div className="source-notation"><div className="source-notation-head"><span className="section-label">{prose ? "Source article" : "Source notation"}</span><span>PDF scan · not transposable</span></div><iframe title={`${song.songNo} ${song.title} source ${prose ? "article" : "notation"}`} src={pdfUrl} loading="lazy" /><a href={pdfUrl} target="_blank" rel="noreferrer noopener">Open the source PDF <Icon name="external" size={16} /></a></div>;
  return <div className="source-notation source-notation-link" data-image-url={imageUrl}><div><span className="section-label">Source notation</span><h3>Notation is available on the authoritative source page</h3><p>This book publishes the page scan and recordings there; this atlas does not redraw it or invent a transposable score.</p></div><a href={pageUrl || imageUrl} target="_blank" rel="noreferrer noopener">Open source page <Icon name="external" size={16} /></a></div>;
}

function SourceRecording({ song, coverage }) {
  const tracks = coverage?.recordingTracks || [];
  const fullTrack = tracks.find((track) => track.isFullSong) || tracks.find((track) => /all\s*4\s*parts/i.test(track.title || ""));
  const [audioFailed, setAudioFailed] = useState(false);
  useEffect(() => setAudioFailed(false), [song?.id, fullTrack?.url]);
  if (!fullTrack?.url) return null;
  const debutRecording = fullTrack.kind === "full-song-source-witness";
  const linkedTracks = tracks.filter((track) => track.url !== fullTrack.url);
  const sourcePages = coverage?.recordingSourcePages || [];
  return <div className="source-recording">
    <div className="source-notation-head"><span className="section-label">Reference audio</span><span>{debutRecording ? "Source witness · does not drive rendering" : "Four parts · does not drive rendering"}</span></div>
    <audio controls preload="none" src={fullTrack.url} aria-label={`${song.songNo} ${song.title} source recording`} onError={() => setAudioFailed(true)} />
    {audioFailed && <p className="source-recording-fallback" role="alert">Reference audio could not be loaded here. Use the preserved recording source links below.</p>}
    {debutRecording && <p className="source-recording-note">Recorded at the official 2025 debut singing. This is source audio only; it does not create or validate transposable notation.</p>}
    <div className="source-recording-links">{linkedTracks.map((track) => <a key={track.url} href={track.url} target="_blank" rel="noreferrer noopener">{track.title.replace(/^\d+\s*[-–]\s*/, "")} <Icon name="external" size={13} /></a>)}{sourcePages.filter((url) => /^https:\/\//.test(url)).map((url) => <a key={url} href={url} target="_blank" rel="noreferrer noopener" aria-label={`Open recording source at ${sourceHostLabel(url)}`}>Open recording source <Icon name="external" size={13} /></a>)}</div>
  </div>;
}

function CleanSourceCandidates({ coverage }) {
  const candidates = coverage?.cleanSourceCandidates || [];
  if (!candidates.length) return null;
  return <div className="clean-source-candidates">
    <div className="source-notation-head"><span className="section-label">Comparison sources</span><span>Not edition-verified</span></div>
    <p>Public score candidates are available for note-for-note comparison. They are not used as the book engraving until the edition match is verified. <a href={assetUrl("/candidate-reconciliation.json")} target="_blank" rel="noreferrer noopener">Open reconciliation ledger <Icon name="external" size={13} /></a></p>
    <div className="clean-source-candidate-list">
      {candidates.map((candidate) => <div className="clean-source-candidate" key={candidate.candidateKey || candidate.pdfUrl}>
        <div><strong>{candidate.title || "Public score candidate"}</strong><span>{candidate.matchKind === "same_text_key" ? "Text/key match" : "Title and text/key match"}{candidate.compositePdfPage ? ` · extracted source page ${candidate.compositePdfPage}` : ""}</span></div>
        <a href={candidate.pdfUrl} target="_blank" rel="noreferrer noopener">Open candidate PDF <Icon name="external" size={14} /></a>
      </div>)}
    </div>
  </div>;
}

function SourceComparisonPanel({ song, bookId, coverage }) {
  const imageUrl = coverage?.sourceImageUrl || "";
  const sourceUrl = coverage?.sourcePageUrl || coverage?.sourceRecordUrl || coverage?.sourceUrls?.[0] || imageUrl;
  const imageOnly = coverage?.sourceImageStatus === "source-observed-image-only";
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => {
    setImageFailed(false);
  }, [song?.id, imageUrl]);
  if (!imageUrl && !sourceUrl) return null;
  const bodyId = `source-comparison-body-${bookId}-${String(song.id).replace(/[^a-z0-9_-]+/gi, "-")}`;
  return <details className="source-comparison-panel">
    <summary aria-controls={bodyId}><span><span className="section-label">Source comparison</span><strong>Open the untouched page image</strong></span><span className="source-comparison-status">Review aid · not transposable</span></summary>
    <div className="source-comparison-body" id={bodyId}>
      <p>{imageOnly ? "This record is preserved as an image-only source witness. It has no transposable score; use the untouched page and recorded source link for verification." : "Compare this recorded source witness directly against the draft. The original is preserved unchanged; cleaned images are only review aids."}</p>
      {imageUrl && !imageFailed && <img src={imageUrl} alt={`${song.songNo} ${song.title} untouched source page`} referrerPolicy="no-referrer" onError={() => setImageFailed(true)} />}
      {imageFailed && <p className="source-comparison-fallback">The page image could not be loaded here.</p>}
      {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer noopener">Open the source page <Icon name="external" size={14} /></a>}
    </div>
  </details>;
}

function ShapeReviewDraftPanel({ reviewItem, ambiguous = false }) {
  const shapeReview = reviewItem?.shapeReviewDraft;
  const draft = shapeReview?.reviewDraft;
  if (!shapeReview || !draft?.publicPath) return null;
  const disposition = reviewDisposition(reviewItem, ambiguous);
  return <section className="shape-review-draft-panel" aria-label="Shape transcription review draft">
    <div className="shape-review-draft-heading"><div><span className="section-label">Shape transcription draft</span><h3>{disposition.heading}</h3></div><span className={`review-only-badge ${disposition.badgeClass}`}>{disposition.badge}</span></div>
    <p>{disposition.summary} Derived from the comparison witness and source key; it cannot replace the source engraving.</p>
    <div className="shape-review-draft-meta"><span><strong>{draft.pitchedEventsRetained}</strong> pitched events</span><span><strong>{draft.sourceKey || "Key not recorded"}</strong>{draft.sourceMode ? ` · ${draft.sourceMode}` : ""}</span><span><strong>{draft.sourceTimeSignature || "Meter not recorded"}</strong></span></div>
    <div className="shape-review-draft-actions"><a href={assetUrl(draft.publicPath)} download={`${reviewItem.songNo}-shape-review.mxl`}>Download review MusicXML <Icon name="download" size={14} /></a><a href={assetUrl("/human-review-queue.json")} target="_blank" rel="noreferrer noopener">Open review evidence <Icon name="external" size={14} /></a></div>
  </section>;
}

function reviewEventsForPart(part, reviewDraft) {
  const events = part?.events || [];
  if (!reviewDraft) return { events, suppressed: 0, collisionGroups: 0 };
  const pitchedByOnset = new Map();
  events.forEach((event) => {
    if (event.rest || !event.step) return;
    const key = `${event.measure || ""}|${Number(event.onset).toFixed(3)}`;
    pitchedByOnset.set(key, (pitchedByOnset.get(key) || 0) + 1);
  });
  const ambiguous = new Set([...pitchedByOnset.entries()].filter(([, count]) => count > 1).map(([key]) => key));
  if (!ambiguous.size) return { events, suppressed: 0, collisionGroups: 0 };
  return {
    events: events.filter((event) => {
      if (event.rest || !event.step) return true;
      const key = `${event.measure || ""}|${Number(event.onset).toFixed(3)}`;
      return !ambiguous.has(key);
    }),
    suppressed: [...pitchedByOnset.values()].filter((count) => count > 1).reduce((total, count) => total + count, 0),
    collisionGroups: ambiguous.size,
  };
}

function ScorePreview({ score, playback, transpose, complete, sourceKey, targetKey, shapeSourceUrl, keyEvidence, sourceTimeSignature, reviewDraft }) {
  const partRows = score?.parts || [];
  const partReviews = partRows.map((part) => reviewEventsForPart(part, reviewDraft));
  const reviewSuppressed = partReviews.reduce((total, review) => total + review.suppressed, 0);
  const reviewCollisionGroups = partReviews.reduce((total, review) => total + review.collisionGroups, 0);
  let measureCount = 0;
  try { measureCount = scoreMeasures(score).length; } catch { /* Engraver exposes source timing failure. */ }
  const noteEvents = partReviews.flatMap((review) => review.events).filter((event) => !event.rest && event.step);
  const shapeStats = noteEvents.reduce((stats, event) => {
    const shape = shapeForScoreEvent(event, sourceKey);
    stats[shape.kind] += 1;
    return stats;
  }, { source: 0, derived: 0, unavailable: 0 });
  const shapeCaption = shapeStats.unavailable === 0
    ? shapeStats.derived > 0 ? "Derived four-shape rendering" : "Source-encoded notehead rendering"
    : "Pitch/rhythm rendering · notehead evidence incomplete";
  const displayedKey = targetKey ? keyLabel(`${targetKey} ${keyMode(sourceKey) || "major"}`) : keyLabel(sourceKey);
  const shapeNote = shapeStats.derived > 0
    ? keyEvidence?.status === "omr-detected"
      ? "Some shapes are derived from an OMR-detected key; verify the key against the source before promotion."
      : keyEvidence?.status === "source-observed"
        ? "Some shapes are derived from the key observed in the source page; human verification is still required."
        : "Some shapes are derived from the recorded source key; the linked source remains authoritative."
      : shapeStats.source > 0
        ? "Encoded noteheads are preserved without inferring a key or mode."
        : "Notehead evidence is unavailable; pitches and rhythms are preserved.";
  const sourceMeasureCount = Number(score?.sourceMeasureCount);
  const measureCaption = complete
    ? sourceMeasureCount && sourceMeasureCount !== measureCount
      ? `${measureCount} detected / ${sourceMeasureCount} source measures · draft view`
      : `${measureCount ? `${measureCount} measures · ` : ""}${score?.reviewPublication?.completeness === "partial" ? "partial-tune view" : "full-song view"}`
    : "loading full song";
  const displayedTimeSignature = score?.timeSignature || sourceTimeSignature || "time not encoded";
  const semantic = scoreSemanticSummary({ ...score, playback });
  return <div className="score-frame">
    <div className="score-caption"><span>{complete ? `${shapeCaption} · ${measureCaption}` : `MusicXML source preview · ${measureCaption}`}</span><span>{displayedKey} · {displayedTimeSignature}</span></div>
    <ScoreEngraving score={score} sourceKey={sourceKey} targetKey={targetKey} transpose={transpose} reviewDraft={reviewDraft} />
    <p className="score-note semantic-summary">Lyrics: {semantic.lyrics} · Repeats: {semantic.repeats} · Endings: {semantic.numberedEndings} · {semantic.playback}</p>
    {reviewSuppressed > 0 && <p className="score-note">{reviewSuppressed} ambiguous OMR notes across {reviewCollisionGroups} onset collisions are hidden in this review view; the raw draft remains preserved.</p>}
    <p className="score-note">{shapeNote}{score?.playbackTransform?.finalChordRemoved && <> Final chord omitted from playback and transposition; source evidence is preserved.</>}{shapeSourceUrl && <> {" "}<a href={shapeSourceUrl} target="_blank" rel="noreferrer noopener">Open shape-source PDF <Icon name="external" size={13} /></a></>}</p>
  </div>;
}

export function App() {
  const [corpus, setCorpus] = useState(null);
  const [corpusAttempt, setCorpusAttempt] = useState(0);
  const [tuneDetail, setTuneDetail] = useState(null);
  const [detailError, setDetailError] = useState(false);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [humanReviewQueue, setHumanReviewQueue] = useState(null);
  const [humanReviewQueueError, setHumanReviewQueueError] = useState(false);
  const [humanReviewQueueAttempt, setHumanReviewQueueAttempt] = useState(0);
  const [bookId, setBookId] = useState(() => {
    try {
      const linkedBook = new URLSearchParams(window.location.search).get("book");
      if (BOOK_ORDER.includes(linkedBook)) return linkedBook;
      const saved = window.localStorage.getItem("sh-corpus-dashboard-book");
      return BOOK_ORDER.includes(saved) ? saved : "sh1991";
    } catch {
      return "sh1991";
    }
  });
  const [mode, setMode] = useState(() => {
    try {
      return window.localStorage.getItem("sh-corpus-dashboard-theme") === "light" ? "light" : "dark";
    } catch {
      return "dark";
    }
  });
  const [query, setQuery] = useState("");
  const [availability, setAvailability] = useState("all");
  const [additionsOnly, setAdditionsOnly] = useState(false);
  const [modeFilter, setModeFilter] = useState("all");
  const [keyFilter, setKeyFilter] = useState("all");
  const [partFilter, setPartFilter] = useState("all");
  const [transposableOnly, setTransposableOnly] = useState(false);
  const [sortOrder, setSortOrder] = useState("page");
  const [resultPage, setResultPage] = useState(0);
  const [linkNotice, setLinkNotice] = useState("");
  const [selectedId, setSelectedId] = useState(() => {
    try {
      const linkedTune = new URLSearchParams(window.location.search).get("tune");
      if (linkedTune) return linkedTune;
      const savedBook = window.localStorage.getItem("sh-corpus-dashboard-book");
      const savedSelections = JSON.parse(window.localStorage.getItem("sh-corpus-dashboard-selected-tunes") || "{}");
      return BOOK_ORDER.includes(savedBook) && savedSelections && typeof savedSelections === "object" && typeof savedSelections[savedBook] === "string"
        ? savedSelections[savedBook]
        : "sh 45t — New Britain";
    } catch {
      return "sh 45t — New Britain";
    }
  });
  const [draftSelection, setDraftSelection] = useState("");
  const [activeSection, setActiveSection] = useState("Library");
  const [targetKey, setTargetKey] = useState("");
  const [activeParts, setActiveParts] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);
  const [tempo, setTempo] = useState(88);
  const [loopCount, setLoopCount] = useState(1);
  const [followRepeats, setFollowRepeats] = useState(false);
  const [playbackProgress, setPlaybackProgress] = useState(0);
  const [playbackNotice, setPlaybackNotice] = useState("");
  const [toast, setToast] = useState("");
  const [fullScore, setFullScore] = useState(null);
  const [scoreLoadAttempt, setScoreLoadAttempt] = useState(0);
  const [scoreLoadError, setScoreLoadError] = useState(false);
  const [sourceKeyOverrides, setSourceKeyOverrides] = useState(() => {
    try {
      const saved = window.localStorage.getItem("sh-corpus-dashboard-source-keys");
      const parsed = saved ? JSON.parse(saved) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  });
  useEffect(() => {
    if (!corpus?.songs) return;
    function openLink() {
      const linked = resolveTuneLink(window.location.href, corpus);
      setLinkNotice(linked?.error || "");
      if (!linked || linked.error) return;
      setBookId(linked.bookId);
      setSelectedId(linked.songId);
      setQuery("");
      setAvailability("all");
      setAdditionsOnly(false);
      setActiveSection("Library");
      setResultPage(0);
    }
    openLink();
    window.addEventListener("popstate", openLink);
    return () => window.removeEventListener("popstate", openLink);
  }, [corpus]);

  useEffect(() => { setResultPage(0); }, [bookId, query, availability, additionsOnly, modeFilter, keyFilter, partFilter, transposableOnly, sortOrder, activeSection]);

  function selectTune(id) {
    setSelectedId(id);
    if (!window.matchMedia('(max-width: 900px)').matches) return;
    window.requestAnimationFrame(() => {
      const details = document.getElementById('selected-tune-details');
      details?.focus({ preventScroll: true });
      details?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    });
  }

  const audioRef = useRef(createAudioState());
  const toastTimerRef = useRef(null);
  const [sourceHealth, setSourceHealth] = useState(null);
  const [sourceHealthAttempt, setSourceHealthAttempt] = useState(0);
  useEffect(() => {
    const audio = audioRef.current;
    audio.disposed = false;
    return () => {
      disposeAudio(audio, window);
      if (toastTimerRef.current !== null) window.clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    };
  }, []);
  useEffect(() => {
    if (audioRef.current.session && !audioRef.current.session.cancelled) stopAudio("Playback stopped because practice settings changed.");
  }, [tempo, loopCount, followRepeats]);

  useEffect(() => {
    const controller = new AbortController();
    setCorpus(null);
    fetch(assetUrl("/reader-data/catalogue.json"), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Corpus request failed: ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (controller.signal.aborted) return;
        validateCorpus(data, BOOK_ORDER);
        if (data.readerDataVersion != null && (data.readerDataVersion !== 1
          || !Array.isArray(data.reviewQueue?.reviewNow)
          || data.reviewQueue.reviewNow.some((item) => !item || typeof item.queueId !== "string" || typeof item.status !== "string")
          || data.songs.some((song) => !/^\/reader-data\/[a-f0-9]{64}\.json$/.test(song.detailRef)))) {
          throw new Error("Incompatible reader catalogue");
        }
        setBookId((current) => data.books[current] ? current : BOOK_ORDER.find((id) => data.books[id]));
        setCorpus(data);
      })
      .catch((error) => { if (!controller.signal.aborted) setCorpus({ error: error.message || "Corpus request failed" }); });
    return () => { controller.abort(); };
  }, [corpusAttempt]);

  useEffect(() => {
    const controller = new AbortController();
    setHumanReviewQueueError(false);
    if (!corpus || corpus.error) return;
    if (corpus.readerDataVersion === 1) {
      setHumanReviewQueue(corpus.reviewQueue);
      return;
    }
    fetch(assetUrl("/human-review-queue.json"), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Review queue request failed: ${response.status}`);
        return response.json();
      })
      .then((data) => { if (!controller.signal.aborted) setHumanReviewQueue(data); })
      .catch(() => {
        if (!controller.signal.aborted) {
          setHumanReviewQueue(null);
          setHumanReviewQueueError(true);
        }
      });
    return () => { controller.abort(); };
  }, [humanReviewQueueAttempt, corpus]);

  useEffect(() => {
    const controller = new AbortController();
    setSourceHealth(null);
    if (!corpus || corpus.error || corpus.readerDataVersion === 1) return;
    fetch(assetUrl("/source-health.json"), { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("health unavailable")))
      .then((data) => {
        if (controller.signal.aborted) return;
        if (!Array.isArray(data?.records) || data.records.some((record) => !record || typeof record.url !== "string")) throw new Error("Invalid source-health bundle");
        setSourceHealth(data);
      })
      .catch(() => { if (!controller.signal.aborted) setSourceHealth({ error: true }); });
    return () => { controller.abort(); };
  }, [sourceHealthAttempt, corpus]);

  const reviewQueueReady = Boolean(humanReviewQueue) && !humanReviewQueueError;

  useEffect(() => {
    try {
      window.localStorage.setItem("sh-corpus-dashboard-source-keys", JSON.stringify(sourceKeyOverrides));
    } catch {
      // Source-key choices remain available for this session when storage is unavailable.
    }
  }, [sourceKeyOverrides]);

  const book = corpus?.books?.[bookId];
  const bookCoverage = corpus?.coverage?.byBook?.[bookId] || { records: 0, localScoreRecords: 0 };
  const unsafeTransposableDrafts = useMemo(() => {
    if (!corpus) return 0;
    return getBookSongs(corpus, bookId).filter((song) => {
      const draft = getBookDraftScore(song, bookId);
      return draft?.transposition?.available && !getBookScore(song, bookId) && !getBookReferenceScore(song, bookId) && (!reviewQueueReady || isRejectedReviewItem(reviewQueueItem(humanReviewQueue, song, bookId)) || reviewQueueIsAmbiguous(humanReviewQueue, song, bookId));
    }).length;
  }, [corpus, humanReviewQueue, humanReviewQueueError, reviewQueueReady, bookId]);
  const transposableCount = Math.max(0, (bookCoverage.transposableRecords || 0) - unsafeTransposableDrafts);
  const transposableDraftCount = Math.max(0, (bookCoverage.transposableDraftRecords || 0) - unsafeTransposableDrafts);
  const coverageSummary = `${formatCount(bookCoverage.transposableLocalScoreRecords || 0)} exact scores, ${formatCount(bookCoverage.transposableReferenceRecords || 0)} reference witnesses, and ${formatCount(transposableDraftCount)} review drafts are transposable; ${formatCount(bookCoverage.keyUnknownStructuredRecords || 0)} structured records remain key-unknown`;

  useEffect(() => {
    if (!book) return;
    const theme = mode === "dark" ? book.darkTheme : book.theme;
    if (!theme) return;
    const root = document.documentElement;
    root.style.setProperty("--pine", theme.surface);
    root.style.setProperty("--pine-raised", theme.surfaceStrong);
    root.style.setProperty("--pine-soft", theme.card);
    root.style.setProperty("--ink", theme.ink);
    root.style.setProperty("--muted", theme.muted);
    root.style.setProperty("--dim", theme.muted);
    root.style.setProperty("--brass", theme.accent);
    root.style.setProperty("--teal", theme.accentSoft);
    root.style.setProperty("--line", theme.border);
    root.style.setProperty("--line-cool", theme.border);
    root.style.setProperty("--page-glow", theme.glow);
    root.style.setProperty("--card", theme.card);
    root.style.setProperty("--shadow", theme.shadow);
    root.style.setProperty("--serif", theme.fonts?.display || "Georgia, serif");
    root.style.setProperty("--body-font", theme.fonts?.body || "Georgia, serif");
    root.style.setProperty("--shape-fa", theme.accent);
    root.style.setProperty("--shape-sol", theme.accentSoft);
    root.style.setProperty("--shape-la", theme.accentStrong);
    root.style.setProperty("--shape-mi", theme.accent);
    document.body.dataset.mode = mode;
    document.body.dataset.book = bookId;
    document.body.dataset.nativeShell = new URLSearchParams(window.location.search).get("nativeShell") === "1" ? "true" : "false";
    window.webkit?.messageHandlers?.atlasTheme?.postMessage({ bookId, mode });
    try {
      window.localStorage.setItem("sh-corpus-dashboard-theme", mode);
      window.localStorage.setItem("sh-corpus-dashboard-book", bookId);
    } catch {
      // The visual theme still applies when storage is unavailable.
    }
  }, [book, bookId, mode]);
  const catalogueSong = corpus?.songs ? corpus.songs.find((song) => song.id === selectedId && song.books.includes(bookId)) || getBookSongs(corpus, bookId)[0] : undefined;

  const detailRef = catalogueSong?.detailRef;
  const currentDetail = tuneDetail && tuneDetail.ref === detailRef ? tuneDetail.data : null;
  const detailReady = !detailRef || Boolean(currentDetail);
  const selectedSong = currentDetail?.song || catalogueSong;
  useEffect(() => {
    if (!detailRef) return;
    const controller = new AbortController();
    setTuneDetail(null);
    setDetailError(false);
    fetch(assetUrl(detailRef), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Tune detail unavailable');
        return response.json();
      })
      .then((data) => {
        validateCorpus({ books: corpus.books, songs: [data.song] }, BOOK_ORDER);
        if (data.song.id !== catalogueSong.id || data.song.books.length !== catalogueSong.books.length
          || !catalogueSong.books.every((book) => data.song.books.includes(book))
          || !Array.isArray(data.reviewQueue?.reviewNow)
          || data.reviewQueue.reviewNow.some((item) => !item || typeof item.queueId !== "string" || typeof item.status !== "string")
          || !Array.isArray(data.sourceHealth?.records)
          || data.sourceHealth.records.some((item) => !item || typeof item.url !== "string")) throw new Error('Incompatible tune detail');
        if (!controller.signal.aborted) setTuneDetail({ ref: detailRef, data });
      })
      .catch(() => { if (!controller.signal.aborted) setDetailError(true); });
    return () => controller.abort();
  }, [detailRef, detailAttempt]);

  useEffect(() => {
    if (!selectedSong) return;
    try {
      const saved = JSON.parse(window.localStorage.getItem("sh-corpus-dashboard-selected-tunes") || "{}");
      const selections = saved && typeof saved === "object" ? saved : {};
      window.localStorage.setItem("sh-corpus-dashboard-selected-tunes", JSON.stringify({ ...selections, [bookId]: selectedSong.id }));
    } catch {
      // The current selection remains available when storage is unavailable.
    }
  }, [bookId, selectedSong?.id]);

  const selectedReviewQueue = currentDetail?.reviewQueue || humanReviewQueue;
  const selectedSourceHealth = detailRef ? currentDetail?.sourceHealth : sourceHealth;
  const reviewDraft = reviewQueueItem(selectedReviewQueue, selectedSong, bookId);
  const reviewDraftAmbiguous = reviewQueueIsAmbiguous(selectedReviewQueue, selectedSong, bookId);
  const rejectedDraft = reviewDraftAmbiguous || isRejectedReviewItem(reviewDraft);
  const selectedScorePreview = detailReady ? getBookScore(selectedSong, bookId) : null;
  const selectedReferenceScore = detailReady ? getBookReferenceScore(selectedSong, bookId) : null;
  const availableDraft = detailReady ? getBookDraftScore(selectedSong, bookId) : null;
  // Pinned publications are a separate reviewed artifact, not the old OMR queue item.
  const publishedDraft = availableDraft?.reviewPublication ? availableDraft : null;
  const selectedDraftScore = publishedDraft || (!reviewQueueReady || rejectedDraft ? null : availableDraft);
  const draftSelectionKey = `${bookId}/${selectedSong?.id || ""}`;
  const preferPublishedDraft = Boolean(publishedDraft && draftSelection === draftSelectionKey);
  const activeScorePreview = preferPublishedDraft ? publishedDraft : selectedScorePreview || selectedReferenceScore || selectedDraftScore;
  const referenceScoreActive = !preferPublishedDraft && !selectedScorePreview && Boolean(selectedReferenceScore);
  const draftScoreActive = preferPublishedDraft || !selectedScorePreview && !selectedReferenceScore && Boolean(selectedDraftScore);
  const selectedMetadata = getBookMetadata(selectedSong, bookId);
  const selectedCoverage = selectedSong?.sourceCoverageByBook?.[bookId];
  const sourceKeyOverrideId = selectedSong ? `${bookId}/${selectedSong.songNo}` : "";
  const enteredSourceKey = sourceKeyOverrides[sourceKeyOverrideId] || "";
  const reviewSourceKey = bookId === "sh2025" && draftScoreActive && !publishedDraft
    ? reviewDraft?.shapeReviewDraft?.reviewDraft?.sourceKey || reviewDraft?.sourceComparison?.sourceMetadata?.key || reviewDraft?.sourceMetadataObservation?.observations?.key?.value || ""
    : "";
  const reviewSourceTimeSignature = bookId === "sh2025" && draftScoreActive && !publishedDraft
    ? reviewDraft?.shapeReviewDraft?.reviewDraft?.sourceTimeSignature || reviewDraft?.sourceComparison?.sourceMetadata?.timeSignature || ""
    : "";
  // Transposition follows the loaded witness itself. A score key wins over
  // catalog metadata for authoritative/reference scores. For an unverified
  // 2025 OMR draft, an explicit source-comparison key takes precedence over
  // the draft's detected key so review playback does not silently transpose
  // from an OMR error.
  const resolvedKey = parseKey(reviewSourceKey)
    ? { value: reviewSourceKey, evidence: { status: "source-observed", source: "untouched 2025 source image observation" } }
    : resolveKeyContext(activeScorePreview, selectedMetadata, enteredSourceKey, { parseKey, keyEvidenceFor, allowMetadataFallback: !referenceScoreActive && !(draftScoreActive && publishedDraft) });
  const sourceKeyValue = resolvedKey.value;
  const shapeSourceKey = sourceKeyValue;
  const sourceKeyName = keyLabel(sourceKeyValue);
  const sourceKeyLabel = keyEvidenceLabel(resolvedKey.evidence, sourceKeyName, referenceScoreActive);
  const sourceMode = keyMode(sourceKeyValue) || "major";
  const transpose = targetKey ? ((ROOT_PITCH[targetKey] - rootFromKey(sourceKeyValue)) + 12) % 12 : 0;
  const signedTranspose = transpose > 6 ? transpose - 12 : transpose;
  const sourceUrls = [...new Set([...(selectedMetadata?.sourceUrl ? [selectedMetadata.sourceUrl] : []), ...(selectedMetadata?.sourceUrls || []), ...(selectedSong?.urls || [])])].slice(0, 6);
  const healthByUrl = useMemo(() => new Map((selectedSourceHealth?.records || []).map((record) => [record.url, record])), [selectedSourceHealth]);
  const rawSelectedHealthRecords = sourceUrls.map((url) => healthByUrl.get(url)).filter(Boolean);
  const selectedHealthPresentation = summarizeSourceHealth(rawSelectedHealthRecords);
  const selectedHealthRecords = rawSelectedHealthRecords;
  const selectedHealthSummary = rawSelectedHealthRecords.length
    ? selectedHealthPresentation.text
    : !selectedSourceHealth ? "Loading source health…" : selectedSourceHealth.error ? "Source-health cache unavailable" : "No health record for this source URL";
  const scoreRef = activeScorePreview?.scoreRef || "";
  const scoreRequestRef = assetUrl(scoreRef);
  const selectedScore = fullScore?.sourceUrl === activeScorePreview?.sourceUrl ? fullScore : activeScorePreview;
  const assetLoaded = Boolean(activeScorePreview && fullScore?.sourceUrl === activeScorePreview.sourceUrl);
  const scoreLoaded = assetLoaded;
  const hasPitchedEvents = Boolean(selectedScore?.parts?.some((part) => (part.events || []).some((event) => !event.rest && event.step)));
  const playbackValidation = activeScorePreview?.playbackValidation || {};
  const quarantine = resolvePlaybackQuarantine(activeScorePreview, fullScore);
  const playbackQuarantined = quarantine.quarantined;
  const playbackAllowed = assetLoaded && !playbackQuarantined;
  const canTranspose = Boolean(!playbackQuarantined && scoreLoaded && hasPitchedEvents && parseKey(sourceKeyValue));
  const repeatPlayback = resolveRepeatPlayback(selectedScore);
  const repeatsAvailable = canApplyPlaybackPlan(repeatPlayback);
  const practicePlayback = followRepeats && repeatsAvailable ? repeatPlayback : null;
  const scoreBadgeLabel = canTranspose
    ? referenceScoreActive ? "Transposable reference" : draftScoreActive ? "Transposable draft" : "Transposable score"
    : referenceScoreActive ? "Structured reference" : draftScoreActive ? "Review draft" : "Structured score";
  const alternateEdition = bookId === "sh2025" && getBookScore(selectedSong, "sh1991") ? "sh1991" : bookId === "sh1991" && getBookScore(selectedSong, "sh2025") ? "sh2025" : "";
  const editionReconciliation = selectedSong?.editionReconciliation;
  const referenceSourceLabel = activeScorePreview?.provenance?.sourceEdition === "sh1991" ? "Sacred Harp 1991" : "another edition/source";
  const matchingResults = useMemo(() => {
    if (!corpus?.songs) return [];
    const normalizedQuery = normalize(query);
    const songs = getBookSongs(corpus, bookId).filter((song) => {
      if (!matchesDiscovery(song, bookId, availability, additionsOnly, { mode: modeFilter === "all" ? "" : modeFilter, key: keyFilter === "all" ? "" : keyFilter, part: partFilter === "all" ? "" : partFilter, transposable: transposableOnly })) return false;
      if (activeSection === "Practice") return getBookScore(song, bookId) || getBookReferenceScore(song, bookId) || (reviewQueueReady && getBookDraftScore(song, bookId) && !isRejectedReviewItem(reviewQueueItem(humanReviewQueue, song, bookId)) && !reviewQueueIsAmbiguous(humanReviewQueue, song, bookId));
      if (activeSection === "Sources") return isSourceRecord(song, bookId);
      return true;
    });
    const matches = songs.filter((song) => { const metadata = getBookMetadata(song, bookId) || {}; const coverage = song.sourceCoverageByBook?.[bookId] || {}; const sourceTerms = [metadata.sourceUrl, ...(metadata.sourceUrls || []), ...(coverage.sourceUrls || []), coverage.editionEvidenceUrl, coverage.sourceImageUrl]; return normalize([song.songNo, song.title, song.rawFirstLine, song.textKey, metadata.composer, metadata.lyricist, coverage.status, coverage.nextAction, ...sourceTerms].join(" ")).includes(normalizedQuery); });
    return sortOrder === "title" ? matches.sort((a, b) => a.title.localeCompare(b.title) || a.songNo.localeCompare(b.songNo, undefined, { numeric: true })) : matches;
  }, [corpus, humanReviewQueue, humanReviewQueueError, reviewQueueReady, bookId, query, activeSection, availability, additionsOnly, modeFilter, keyFilter, partFilter, transposableOnly, sortOrder]);
  useEffect(() => {
    if (matchingResults.length && selectedSong && !matchingResults.some((song) => song.id === selectedSong.id)) {
      setSelectedId(matchingResults[0].id);
    }
  }, [matchingResults, selectedSong?.id]);

  const pageCount = Math.max(1, Math.ceil(matchingResults.length / 80));
  const visiblePage = Math.min(resultPage, pageCount - 1);
  const results = matchingResults.slice(visiblePage * 80, (visiblePage + 1) * 80);


  useEffect(() => {
    const controller = new AbortController();
    setFullScore(null);
    setFollowRepeats(false);
    setScoreLoadError(false);
    if (!scoreRef) return () => { controller.abort(); };
    fetch(scoreRequestRef, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Score request failed: ${response.status}`);
        return response.json();
      })
      .then((score) => { if (!controller.signal.aborted) setFullScore(score); })
      .catch(() => { if (!controller.signal.aborted) { setFullScore(null); setScoreLoadError(true); } });
    return () => { controller.abort(); };
  }, [scoreRequestRef, scoreLoadAttempt]);

  useEffect(() => {
    if (!selectedSong) return;
    setTargetKey("");
    setActiveParts(activeScorePreview?.parts?.map((part) => part.name) || []);
    stopAudio("Playback stopped because the selected tune changed.");
  }, [selectedId, bookId, scoreRef]);

  if (!corpus) return <div className="loading-screen" role="status" aria-live="polite">Loading the local atlas…</div>;
  if (corpus.error) return <div className="loading-screen" role="alert"><Icon name="info" size={22} /><p>The local corpus bundle could not be loaded or is incompatible. Check the static host and refresh the bundle, then retry.</p><button className="text-button" type="button" onClick={() => setCorpusAttempt((attempt) => attempt + 1)}>Retry loading</button></div>;

  function stopAudio(notice = "") {
    const audio = audioRef.current;
    const wasPlaying = audio.nodes.size > 0 || Boolean(audio.master) || Boolean(audio.session);
    stopAudioResources(audio, window);
    if (audio.disposed) return;
    setPlaying(false);
    setPaused(false);
    setPlaybackProgress(0);
    if (notice && wasPlaying) setPlaybackNotice(notice);
  }

  async function playAvailableParts() {
    if (audioRef.current.disposed || !playbackAllowed || !selectedScore || !activeParts.length) return;
    setPlaybackNotice("");
    stopAudio();
    const generation = audioRef.current.generation;
    const session = { generation, cancelled: false }; session.owner = session;
    audioRef.current.session = session;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      showToast("Audio playback is not supported in this browser.");
      return;
    }
    let context = audioRef.current.context;
    if (!context || context.state === "closed") context = new AudioContextClass();
    audioRef.current.context = context;
    try {
      if (context.state !== "running") await context.resume();
      if (audioRef.current.disposed || !sessionIsCurrent(audioRef.current.session, session) || audioRef.current.generation !== generation) return;
      if (context.state !== "running") {
        showToast("Audio is unavailable until the browser allows playback.");
        return;
      }
    } catch {
      if (audioRef.current.disposed || !sessionIsCurrent(audioRef.current.session, session)) return;
      showToast("Audio could not start. Check the browser's audio permission.");
      return;
    }
    const now = context.currentTime + 0.08;
    const beatSeconds = 60 / Math.max(40, Math.min(220, tempo));
    const boundedLoops = Math.max(1, Math.min(8, Number(loopCount) || 1));
    const parts = selectedScore.parts.filter((part) => activeParts.includes(part.name)).map((part) => ({
      ...part,
      events: reviewEventsForPart(part, draftScoreActive).events,
    }));
    const practiceSchedule = buildPracticeSchedule(parts, practicePlayback, boundedLoops);
    Object.assign(session, { startedAt: now, duration: practiceSchedule.duration * beatSeconds + 0.5 });
    const schedulingFailed = (error) => {
      if (audioRef.current.disposed) return;
      stopAudio();
      console.error("Sacred Harp audio scheduling failed", error);
      showToast("Audio could not be scheduled for this score.");
    };
    try {
      const scheduled = schedulePracticeAudio(audioRef.current, session, practiceSchedule.events, {
        startedAt: now, beatSeconds, partNames: parts.map((part) => part.name), pitchToMidi,
        transpose: signedTranspose, onError: schedulingFailed, timers: window,
      });
      if (!scheduled) {
        if (sessionIsCurrent(audioRef.current.session, session)) {
          stopAudio();
          showToast("This score has no playable pitched events.");
        }
        return;
      }
    } catch (error) { schedulingFailed(error); return; }
    setPlaying(true);
    audioRef.current.progressTimer = window.setInterval(() => {
      const session = audioRef.current.session;
      if (!session || !sessionIsCurrent(audioRef.current.session, session) || session.generation !== audioRef.current.generation) return;
      const elapsed = Math.max(0, context.currentTime - session.startedAt);
      setPlaybackProgress(Math.min(1, elapsed / session.duration));
      if (shouldCompleteSession(context.currentTime, session)) stopAudio();
    }, 100);
  }

  async function togglePause() {
    const context = audioRef.current.context;
    if (!playing || !context) return;
    const session = audioRef.current.session;
    const generation = audioRef.current.generation;
    try {
      const nextPaused = context.state === "running";
      const stillCurrent = await guardedAudioAction(() => nextPaused ? context.suspend() : context.resume(), audioRef.current.session, session);
      if (!stillCurrent || audioRef.current.generation !== generation) return;
      setPaused(nextPaused);
    } catch { if (sessionIsCurrent(audioRef.current.session, session)) showToast("Audio could not change pause state."); }
  }

  function handleBookChange(nextBookId) {
    setBookId(nextBookId);
    setAdditionsOnly(false);
    setLinkNotice("");
    const next = getBookSongs(corpus, nextBookId)[0];
    if (next) setSelectedId(next.id);
  }

  function toggleTheme() {
    setMode((current) => current === "dark" ? "light" : "dark");
  }

  function togglePart(name) {
    stopAudio("Playback stopped because the selected parts changed.");
    setActiveParts((current) => current.includes(name) ? current.filter((part) => part !== name) : [...current, name]);
  }

  function setEnteredSourceKey(value) {
    if (!sourceKeyOverrideId) return;
    stopAudio("Playback stopped because the source key changed.");
    setSourceKeyOverrides((current) => {
      const next = { ...current };
      if (value) next[sourceKeyOverrideId] = value;
      else delete next[sourceKeyOverrideId];
      return next;
    });
    setTargetKey("");
  }

  function nudgeTranspose(direction) {
    if (!sourceKeyValue) return;
    const current = targetKey ? rootFromKey(targetKey) : rootFromKey(sourceKeyValue);
    const nextPitch = (current + direction + 12) % 12;
    stopAudio("Playback stopped because the target key changed.");
    setTargetKey(KEY_NAMES[nextPitch]);
  }

  function showToast(message) {
    if (audioRef.current.disposed) return;
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    setToast(message);
    toastTimerRef.current = window.setTimeout(() => {
      setToast("");
      toastTimerRef.current = null;
    }, 2600);
  }

  const bookSongs = getBookSongs(corpus, bookId);
  const scoreError = scoreLoadError;
  const discoveredKeys = [...new Set(bookSongs.map((song) => recordKey(song, bookId)).filter(Boolean).map((key) => key.split(' ')[0]))].sort();
  const discoveredParts = [...new Set(bookSongs.flatMap((song) => (getBookScore(song, bookId) || getBookReferenceScore(song, bookId) || getBookDraftScore(song, bookId))?.parts?.map((part) => part.name) || []).filter(Boolean))].sort();
  const proseCount = bookSongs.filter((song) => song.sourceCoverageByBook?.[bookId]?.contentKind === "prose").length;
  const bookRecordSummary = `${formatCount(bookSongs.length - proseCount)} tunes${proseCount ? ` · ${formatCount(proseCount)} articles` : ""}`;
  const resultSummary = `${formatCount(matchingResults.length)} matches · ${bookRecordSummary}`;
  function changeResultPage(nextPage) {
    setResultPage(nextPage);
    document.querySelector(".results-list")?.scrollTo({ top: 0 });
  }

  const practiceTransport = <>
            {(!sourceKeyValue || resolvedKey.evidence?.status === "entered") && <div className="source-key-picker"><div><span className="section-label">{sourceKeyValue ? "Entered source key" : "Source key required"}</span><p>{sourceKeyValue ? "Change this if the key printed in the source differs." : "Choose the key printed in this source to unlock pitch-accurate transposition."}</p></div><label className="key-select-wrap"><span className="sr-only">Source key</span><select aria-label="Source key" value={enteredSourceKey} onChange={(event) => setEnteredSourceKey(event.target.value)}><option value="">Choose source key…</option>{["major", "minor"].flatMap((mode) => KEY_NAMES.map((key) => <option key={`${key}:${mode}`} value={`${key}:${mode}`}>{key} {mode}</option>))}</select><span className="select-chevron">⌄</span></label></div>}
            <div className="transport-row"><div className="playback-controls"><button className="primary-button" onClick={playing ? () => stopAudio() : scoreLoadError ? () => setScoreLoadAttempt((attempt) => attempt + 1) : playAvailableParts} disabled={scoreLoadError ? false : !playbackAllowed || !activeParts.length}>{playing ? <Icon name="stop" size={14} /> : <Icon name="play" size={15} />}{playing ? "Stop" : scoreError ? "Retry loading" : playbackQuarantined ? "Playback unavailable" : scoreLoaded ? "Play song" : "Loading…"}</button>{playing && <button className="secondary-button" onClick={togglePause}><Icon name="pause" size={14} />{paused ? "Resume" : "Pause"}</button>}</div><div className="practice-options"><label>Order <select aria-label="Playback order" value={followRepeats && repeatsAvailable ? "repeats" : "written"} onChange={(event) => setFollowRepeats(event.target.value === "repeats")}><option value="written">Written order</option><option value="repeats" disabled={!repeatsAvailable}>Follow encoded repeats</option></select></label><label>Tempo <input aria-label="Tempo BPM" type="number" min="40" max="220" value={tempo} onChange={(event) => setTempo(Math.max(40, Math.min(220, Number(event.target.value) || 88)))} /> BPM</label><label>Loops <select aria-label="Playback loops" value={loopCount} onChange={(event) => setLoopCount(Number(event.target.value))}>{[1,2,3,4,5,6,7,8].map((count) => <option key={count} value={count}>{count}</option>)}</select></label></div><div className="transpose-controls"><button className="secondary-button" title="Transpose down one semitone" aria-label="Transpose down one semitone" onClick={() => nudgeTranspose(-1)} disabled={!canTranspose}><Icon name="arrowDown" size={16} />Down</button><label className="key-select-wrap"><span className="sr-only">Target key</span><select aria-label="Target key" value={targetKey} onChange={(event) => { stopAudio("Playback stopped because the target key changed."); setTargetKey(event.target.value); }} disabled={!canTranspose}><option value="">{sourceKeyName}</option>{KEY_NAMES.filter((key) => key !== sourceKeyName.split(" ")[0]).map((key) => <option key={key} value={key}>{key} {sourceMode}</option>)}</select><span className="select-chevron">⌄</span></label><button className="secondary-button" title="Transpose up one semitone" aria-label="Transpose up one semitone" onClick={() => nudgeTranspose(1)} disabled={!canTranspose}><Icon name="arrowUp" size={16} />Up</button></div></div><div className="practice-progress" role="progressbar" aria-label="Playback progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(Math.max(0, Math.min(1, playbackProgress)) * 100)}><span style={{ width: `${playbackProgress * 100}%` }} /></div>
            {scoreRef && !scoreLoaded && !scoreLoadError && <div className="sr-only" role="status" aria-live="polite">Loading the structured score…</div>}
            {scoreLoadError && <div className="score-load-error" role="alert"><Icon name="info" size={16} /><span>The full score could not be loaded. Check the local server, then retry.</span></div>}
            {signedTranspose !== 0 && <div className="transposition-note" role="status" aria-live="polite" aria-atomic="true"><span>Transposed {signedTranspose > 0 ? "+" : "−"}{Math.abs(signedTranspose)} semitone{Math.abs(signedTranspose) === 1 ? "" : "s"} from {sourceKeyName}</span></div>}
            <div className="structured-score-status"><Icon name={draftScoreActive || !canTranspose ? "info" : "check"} size={16} /><span>{draftScoreActive ? "Draft loaded for review playback and transposition; source comparison is still required." : "Structured source loaded for playback."} {sourceKeyValue ? `${sourceKeyLabel}.` : "Choose the source key above to enable transposition."}</span></div>
  </>;

  return <div className="app-shell">
    <a className="skip-link" href="#selected-tune-details">Skip to selected tune details</a>
    <header className="atlas-header">
      <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">◇</div><h1>Shape-Note Atlas</h1></div>
      <nav className="primary-nav" aria-label="Primary navigation">
        {[{ label: "Library", icon: "book" }, { label: "Practice", icon: "practice" }, { label: "Sources", icon: "source" }].map((item) => <button key={item.label} className={`nav-item ${activeSection === item.label ? "active" : ""}`} aria-current={activeSection === item.label ? "page" : undefined} onClick={() => setActiveSection(item.label)}><Icon name={item.icon} /><span>{item.label}</span></button>)}
      </nav>
      <div className="header-controls">
        <label className="book-select-wrap header-book-picker" htmlFor="book-select"><span className="sr-only">Tune book</span><Icon name="book" size={18} /><select id="book-select" aria-label="Tune book" value={bookId} onChange={(event) => handleBookChange(event.target.value)}>{BOOK_ORDER.filter((id) => corpus.books[id]).map((id) => <option key={id} value={id}>{corpus.books[id].label}</option>)}</select><span className="select-chevron">⌄</span></label>
        <span className="coverage-summary" title={coverageSummary}><span aria-hidden="true">{formatCount(transposableCount)} transposable · {bookRecordSummary}</span><span className="sr-only">{coverageSummary}</span></span>
        <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${mode === "dark" ? "light" : "dark"} mode`}>{mode === "dark" ? "Light" : "Dark"}</button>
      </div>
    </header>

    <main className="workspace">
      <section className="results-column" aria-label="Tune search results">
        <div className="results-head"><div className="search-box"><Icon name="search" size={20} /><input data-testid="tune-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tunes, pages, first lines, or sources" aria-label="Search tune, page, first line, or source metadata" />{query && <button className="clear-search" onClick={() => setQuery("")} aria-label="Clear search">×</button>}</div><div className="discovery-controls">
          <label>Notation<select aria-label="Notation availability" value={availability} onChange={(event) => setAvailability(event.target.value)}><option value="all">All records</option><option value="exact">Catalogued score</option><option value="reference">Alternate reference</option><option value="draft">Review draft only</option><option value="source-only">No structured notation</option><option value="prose">Prose articles</option></select></label>
          <label>Key<select aria-label="Key filter" value={keyFilter} onChange={(event) => setKeyFilter(event.target.value)}><option value="all">All keys</option>{discoveredKeys.map((key) => <option key={key} value={key}>{key}</option>)}</select></label>
          <label>Mode<select aria-label="Mode filter" value={modeFilter} onChange={(event) => setModeFilter(event.target.value)}><option value="all">All modes</option><option value="major">Major</option><option value="minor">Minor</option><option value="unknown">Mode unavailable</option></select></label>
          <label>Part<select aria-label="Available part filter" value={partFilter} onChange={(event) => setPartFilter(event.target.value)}><option value="all">Any part</option>{discoveredParts.map((part) => <option key={part} value={part}>{part}</option>)}</select></label>
          <label className="additions-filter"><input type="checkbox" checked={transposableOnly} onChange={(event) => setTransposableOnly(event.target.checked)} />Transposable</label>
          <label>Sort<select aria-label="Sort tunes" value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}><option value="page">Page order</option><option value="title">Title A–Z</option></select></label>
          {bookId === "sh2025" && <label className="additions-filter"><input type="checkbox" checked={additionsOnly} onChange={(event) => setAdditionsOnly(event.target.checked)} />New in 2025</label>}
          {(availability !== "all" || additionsOnly || query || modeFilter !== "all" || keyFilter !== "all" || partFilter !== "all" || transposableOnly) && <button className="text-button" onClick={() => { setAvailability("all"); setAdditionsOnly(false); setModeFilter("all"); setKeyFilter("all"); setPartFilter("all"); setTransposableOnly(false); setQuery(""); }}>Clear filters</button>}
        </div><div className="results-kicker">{activeSection}</div><div className="results-summary" aria-live="polite" aria-atomic="true">{resultSummary}</div></div>
        <div className="results-list">
        {results.length ? results.map((song) => { const sourceStatus = sourceRowStatus(song, bookId); const reviewItem = reviewQueueItem(humanReviewQueue, song, bookId); const reviewAmbiguous = reviewQueueIsAmbiguous(humanReviewQueue, song, bookId); const rowStatus = activeSection === "Sources" ? <span className="tiny-status source-status"><Icon name={sourceStatus.icon} size={13} />{sourceStatus.label}</span> : song.sourceCoverageByBook?.[bookId]?.contentKind === "prose" ? <span className="tiny-status muted">article</span> : getBookScore(song, bookId) ? <span className="tiny-status"><Icon name="check" size={13} />score</span> : getBookReferenceScore(song, bookId) ? <span className="tiny-status"><Icon name="check" size={13} />reference</span> : reviewAmbiguous ? <span className="tiny-status ambiguous-evidence">ambiguous</span> : isRejectedReviewItem(reviewItem) ? <span className="tiny-status rejected-source-mismatch">rejected</span> : reviewItem?.status === "autonomously-blocked" ? <span className="tiny-status autonomously-blocked">blocked</span> : !reviewQueueReady && getBookDraftScore(song, bookId) ? <span className="tiny-status muted">checking</span> : getBookDraftScore(song, bookId) ? <span className="tiny-status draft-status">draft</span> : <span className="tiny-status muted"><Icon name="info" size={13} />metadata</span>; return <button key={song.id} className={`result-row ${song.id === selectedSong?.id ? "selected" : ""}`} aria-current={song.id === selectedSong?.id ? "true" : undefined} onClick={() => selectTune(song.id)}><div className="result-copy"><span className="result-number">{song.songNo}</span><strong>{song.title}</strong><span>{song.rawFirstLine || song.textKey}</span></div><div className="result-status">{rowStatus}<Icon name="chevron" size={17} /></div></button>; }) : <div className="empty-results"><Icon name="search" size={23} /><h3>No matching records</h3><p>{activeSection === "Sources" ? "No source records match these filters." : "Try another search or clear the filters."}</p></div>}
        </div>
        <nav className="result-pagination" aria-label="Results pages"><button className="text-button" disabled={visiblePage === 0} onClick={() => changeResultPage(visiblePage - 1)}>Previous</button><span aria-live="polite">Page {visiblePage + 1} of {pageCount}</span><button className="text-button" disabled={visiblePage + 1 >= pageCount} onClick={() => changeResultPage(visiblePage + 1)}>Next</button></nav>
      </section>

      <section className="detail-column" id="selected-tune-details" aria-label="Selected tune details" tabIndex="-1">
        {linkNotice && <p className="source-coverage-note" role="status">{linkNotice}</p>}
        {selectedSong ? <>
          <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">Selected tune: {selectedSong.songNo} — {selectedSong.title}</div>
          <div className="detail-header"><div><div className="detail-overline">{book.label} · page {selectedSong.songNo}</div><h2>{selectedSong.songNo} — {selectedSong.title}</h2></div><button className="icon-button" aria-label="Show source preservation note" onClick={() => showToast("Source links and score data are preserved locally.")}><Icon name="info" size={20} /></button></div>
          <a className="tune-link" href={tuneUrl(window.location.href, bookId, selectedSong.id)}>{selectedCoverage?.contentKind === "prose" ? "Link to this article" : "Link to this tune"}</a>
          {!detailReady ? <div className="source-coverage-note" role={detailError ? "alert" : "status"}>
            <p>{detailError ? "Tune evidence could not be loaded. Playback remains unavailable." : "Loading tune evidence…"}</p>
            {detailError && <button className="text-button" onClick={() => setDetailAttempt((attempt) => attempt + 1)}>Retry tune evidence</button>}
          </div> : <>
          <div className="detail-tags">{selectedScore ? <span className={`tag ${canTranspose ? referenceScoreActive ? "reference-tag" : draftScoreActive ? "draft-tag" : "available" : "unavailable"}`}><Icon name={canTranspose ? "check" : "info"} size={14} />{scoreBadgeLabel}</span> : selectedCoverage?.status === "transcription-blocked" ? <span className="tag unavailable"><Icon name="info" size={14} />Transcription blocked</span> : sourcePdfUrl(selectedSong) || sourcePageUrl(selectedSong, bookId) ? <span className="tag available"><Icon name="check" size={14} />Source scan</span> : selectedCoverage?.status === "source-reference" ? <span className="tag available"><Icon name="check" size={14} />Source reference</span> : <span className="tag unavailable"><Icon name="info" size={14} />Metadata only</span>}{(selectedScore || sourceKeyValue || draftScoreActive) && <span className="tag key-tag">{sourceKeyValue ? sourceKeyLabel : "Key unavailable"}</span>}{bookId === "sh2025" && selectedMetadata?.editionStatus === "added-in-2025" && <span className="tag edition-new-tag">New in 2025</span>}{editionReconciliation && <span className="tag edition-tag">{editionReconciliation.status === "change-flagged" ? "1991 / 2025 text differs" : "Shared by 1991 / 2025"}</span>}</div>
          {selectedSong.sourceIdentityReview && <div className="source-coverage-note"><Icon name="info" size={18} /><span><strong>{selectedSong.sourceIdentityReview.contentKind === "prose" ? "Article, not a notation page." : "Source page identified."}</strong> Printed page {selectedSong.sourceIdentityReview.printedPage}; PDF leaf {selectedSong.sourceIdentityReview.pdfLeaf}. {selectedSong.sourceIdentityReview.observation} <a href={selectedSong.sourceIdentityReview.sourceUrl} target="_blank" rel="noreferrer noopener">Open reviewed source page</a></span></div>}
          <div className="first-line"><span className="section-label">{selectedCoverage?.contentKind === "prose" ? "Catalogue text extract" : "First line"}</span><p>{selectedSong.rawFirstLine || "No first line recorded in the local source."}</p></div>
          {humanReviewQueueError && selectedCoverage && selectedCoverage.status !== "structured-score" && <div className="source-coverage-note"><Icon name="info" size={18} /><span role="status"><strong>Review status unavailable.</strong> The local human-review queue could not be loaded. Source coverage and score data are unchanged; reload when the local server is available.</span><button className="text-button" type="button" onClick={() => setHumanReviewQueueAttempt((attempt) => attempt + 1)}>Retry</button></div>}
          {publishedDraft && (selectedScorePreview || selectedReferenceScore) && <div className="source-key-picker"><div><span className="section-label">Score version</span><p>A corrected practice draft is available. The existing score is preserved.</p></div><label className="key-select-wrap"><span className="sr-only">Score version</span><select aria-label="Score version" value={preferPublishedDraft ? "draft" : "existing"} onChange={(event) => { stopAudio("Playback stopped because the score version changed."); setDraftSelection(event.target.value === "draft" ? draftSelectionKey : ""); }}><option value="existing">Existing structured score</option><option value="draft">Correction draft {publishedDraft.reviewPublication.version}</option></select><span className="select-chevron">⌄</span></label></div>}
          {selectedScore ? <>
            {referenceScoreActive && <div className="reference-score-note"><Icon name="info" size={18} /><span>This is a transposable reference witness from {referenceSourceLabel}. It is shown for practice, but it is not being presented as the {book.label} engraving.</span></div>}
            {draftScoreActive && <div className="draft-score-note"><Icon name="info" size={18} /><span>{reviewDraft && !publishedDraft ? <><strong>{reviewDisposition(reviewDraft, reviewDraftAmbiguous).label}.</strong> {reviewDisposition(reviewDraft, reviewDraftAmbiguous).summary} </> : selectedDraftScore?.reviewPublication ? "This is a published working transcription. " : "This is an unverified OMR transcription draft. "}{selectedDraftScore?.reviewPublication ? "Ready for practice and correction; not yet a verified edition score. " : <>It is playable and transposable only as isolated review material, but it is not the {book.label} engraving and does not count as verified coverage. </>}<a href={assetUrl(selectedDraftScore?.reviewPublication?.evidenceUrl || "/human-review-queue.json")} target="_blank" rel="noreferrer noopener">{reviewDraft && !publishedDraft ? "View disposition evidence" : "Open review evidence"} <Icon name="external" size={13} /></a></span></div>}
            {selectedCoverage?.status === "transcription-blocked" && <div className="source-coverage-note"><Icon name="info" size={18} /><span><strong>Source coverage blocked.</strong> {coverageNextStep(selectedCoverage)} This review draft remains isolated until an authorized source is acquired.</span></div>}
            {draftScoreActive && <PublishedDraftActions draft={selectedDraftScore} song={selectedSong} bookLabel={book.label} assetUrl={assetUrl} />}
            {draftScoreActive && !publishedDraft && <CleanSourceCandidates coverage={selectedCoverage} />}
            {draftScoreActive && !publishedDraft && <SourceComparisonPanel song={selectedSong} bookId={bookId} coverage={selectedCoverage} />}
            {draftScoreActive && !publishedDraft && <ShapeReviewDraftPanel reviewItem={reviewDraft} ambiguous={reviewDraftAmbiguous} />}
            <div className="parts-heading"><span className="section-label">Available parts</span><span className="parts-count">{activeParts.length} of {selectedScore.parts.length} selected</span></div>
            <div className="part-toggles" role="group" aria-label="Available parts">{selectedScore.parts.map((part, partIndex) => <button key={part.name} className={`part-toggle ${activeParts.includes(part.name) ? "selected" : ""}`} aria-pressed={activeParts.includes(part.name)} disabled={playing} onClick={() => togglePart(part.name)}><span className="part-clef">{partClefGlyph(part, partIndex)}</span><span>{part.name}</span><span className="part-check"><Icon name="check" size={13} /></span></button>)}</div>
            {activeSection === "Practice" && <section aria-label="Practice controls"><div className="parts-heading"><span className="section-label">Practice this tune</span></div>{practiceTransport}</section>}
            <ScorePreview score={selectedScore} playback={practicePlayback} transpose={signedTranspose} complete={assetLoaded} sourceKey={shapeSourceKey} targetKey={targetKey} shapeSourceUrl={shapeSourcePdfUrl(activeScorePreview)} keyEvidence={resolvedKey.evidence} sourceTimeSignature={reviewSourceTimeSignature} reviewDraft={draftScoreActive} />
            {activeSection !== "Practice" && practiceTransport}
            {draftScoreActive && <SourceRecording song={selectedSong} coverage={selectedCoverage} />}
          </> : <><div className="missing-score"><Icon name="info" size={23} /><div><h3>{selectedCoverage?.contentKind === "prose" ? "Prose article — no score expected" : "No transposable score file for this record"}</h3><p>{selectedCoverage?.contentKind === "prose" ? "This reviewed article is preserved for reference and excluded from tune counts and the notation transcription queue." : "The atlas preserves the exact source link or scan instead of synthesizing notation where structured score data is absent."}</p>{selectedCoverage && <p className="edition-note"><strong>{coverageLabel(selectedCoverage)}.</strong> {coverageNextStep(selectedCoverage)}</p>}{selectedCoverage?.editionStatus === "added-in-2025" && <p className="edition-note"><strong>New in 2025.</strong> This page is on the publisher's additions list and has no verified 2025 MusicXML yet. <a href={selectedCoverage.editionEvidenceUrl} target="_blank" rel="noreferrer noopener">View the source list <Icon name="external" size={13} /></a></p>}{reviewDraft && <p className="edition-note"><strong>{reviewDisposition(reviewDraft, reviewDraftAmbiguous).label}.</strong> {reviewDisposition(reviewDraft, reviewDraftAmbiguous).summary} {reviewDraft.draftSummary.parts} parts, {Object.values(reviewDraft.draftSummary.measuresByPart)[0] || "unknown"} measures per part. It is not playable or transposable because the source comparison is not promotion-safe. <a href={assetUrl("/human-review-queue.json")} target="_blank" rel="noreferrer noopener">View disposition evidence <Icon name="external" size={13} /></a></p>}{alternateEdition && <p className="edition-note">A verified {alternateEdition === "sh1991" ? "1991" : "2025"}-edition score is available for this shared tune, but it is not being mislabeled as a {bookId === "sh2025" ? "2025" : "1991"} score.</p>}{alternateEdition && <button className="text-button" onClick={() => { setBookId(alternateEdition); setSelectedId(selectedSong.id); }}>Open the verified {alternateEdition === "sh1991" ? "1991" : "2025"} score</button>}</div></div><ShapeReviewDraftPanel reviewItem={reviewDraft} ambiguous={reviewDraftAmbiguous} /><CleanSourceCandidates coverage={selectedCoverage} /><SourceNotation song={selectedSong} bookId={bookId} /><SourceComparisonPanel song={selectedSong} bookId={bookId} coverage={selectedCoverage} /><SourceRecording song={selectedSong} coverage={selectedCoverage} /></>}
          <div className="source-strip"><div><span className="section-label">Source</span><span>{selectedMetadata?.sourceUrl ? `${book.label}, page ${selectedSong.songNo}` : "Local corpus record"}</span></div><div className="source-actions">{sourceUrls.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer noopener" aria-label={`Open source record at ${sourceDestinationLabel(url)}`}>Open source record <Icon name="external" size={16} /></a>)}{activeScorePreview && shapeSourcePdfUrl(activeScorePreview) && <a href={shapeSourcePdfUrl(activeScorePreview)} target="_blank" rel="noreferrer noopener">Open shape-source PDF <Icon name="external" size={16} /></a>}</div></div>
          <div className="source-health-card" aria-label="Source health" aria-busy={!selectedSourceHealth}><div><span className="section-label">Source health</span><strong role="status" aria-live="polite">{selectedHealthSummary}</strong>{selectedSourceHealth?.error && <button className="text-button" type="button" onClick={() => setSourceHealthAttempt((attempt) => attempt + 1)}>Retry source health</button>}</div><span className="source-health-retention">{selectedHealthPresentation.retentionLabel}</span></div>
          {repeatPlayback?.status === "blocked" && <p className="practice-fallback-note" role="status">Repeat playback is unavailable: {repeatPlayback.reason} Practice uses written order.</p>}
          {playbackQuarantined && <p className="practice-fallback-note" role="alert"><strong>Playback unavailable.</strong> {quarantine.reason}</p>}
          <div className="detail-footer"><ShapeLegend /></div>
          </>}
        </> : <div className="missing-score"><Icon name="info" size={23} /><div><h3>Select a tune to begin</h3><p>Search the local atlas by page, title, or first line.</p></div></div>}
      </section>
    </main>
    {toast && <div className="toast" role="status"><Icon name="check" size={16} />{toast}</div>}
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{playbackNotice}</div>
  </div>;
}

export function mountAtlas(element) {
  const root = createRoot(element);
  root.render(<App />);
  return root;
}

export const atlasRoot = mountAtlas(document.getElementById("root"));
