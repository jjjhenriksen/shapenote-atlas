import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const BOOK_ORDER = ["sh1991", "sh2025", "shcooper2012", "ch7", "shenandoah", "southernharmony", "kentucky", "socialharp", "mnharmony", "sacredharptunes", "trumpet"];
const KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const ROOT_PITCH = { C: 0, "B#": 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4, "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11 };
const STEP_SEMITONES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const STEP_DIATONIC = { C: 0, D: 1, E: 2, F: 3, G: 4, A: 5, B: 6 };
const SACRED_HARP_MAJOR_SHAPES = ["fa", "sol", "la", "fa", "sol", "la", "mi"];
const SHAPE_NAMES = new Set(["fa", "sol", "la", "mi"]);
const DIATONIC_STEPS = ["C", "D", "E", "F", "G", "A", "B"];

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
  return data.songs.filter((song) => song.books.includes(bookId));
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

function parseKey(key) {
  if (!key) return null;
  const value = String(key).trim();
  const fifthsMap = { "-7": "Cb", "-6": "Gb", "-5": "Db", "-4": "Ab", "-3": "Eb", "-2": "Bb", "-1": "F", "0": "C", "1": "G", "2": "D", "3": "A", "4": "E", "5": "B", "6": "F#", "7": "C#" };
  const minorFifthsMap = { "-7": "Ab", "-6": "Eb", "-5": "Bb", "-4": "F", "-3": "C", "-2": "G", "-1": "D", "0": "A", "1": "E", "2": "B", "3": "F#", "4": "C#", "5": "G#", "6": "D#", "7": "A#" };
  let tonic = "";
  let mode = "major";
  if (value.includes(":")) {
    const pieces = value.split(":");
    if (pieces.length !== 2) return null;
    const [tonicOrFifths, encodedMode] = pieces.map((piece) => piece.trim());
    mode = encodedMode.toLowerCase();
    if (!['major', 'minor'].includes(mode)) return null;
    tonic = ROOT_PITCH[tonicOrFifths] !== undefined ? tonicOrFifths : (mode === "minor" ? minorFifthsMap : fifthsMap)[tonicOrFifths] || "";
  } else {
    const match = value.match(/^([A-G](?:#|b)?)(?:\s+(major|minor))?$/i);
    if (!match) return null;
    tonic = match[1][0].toUpperCase() + match[1].slice(1);
    mode = (match[2] || "major").toLowerCase();
  }
  const rootPitch = ROOT_PITCH[tonic];
  if (rootPitch === undefined) return null;
  return { rootName: tonic, rootPitch, mode, tonicStep: tonic[0].toUpperCase() };
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

function keyContext(score, metadata, enteredKey = "") {
  const scoreKey = score?.keySignature || "";
  if (parseKey(scoreKey)) return { value: scoreKey, evidence: keyEvidenceFor(score) };
  const metadataKey = metadata?.keySignature || "";
  if (parseKey(metadataKey)) return { value: metadataKey, evidence: keyEvidenceFor(metadata) };
  if (parseKey(enteredKey)) return { value: enteredKey, evidence: { status: "entered", source: "user-entered source key" } };
  return { value: "", evidence: keyEvidenceFor(score, keyEvidenceFor(metadata)) };
}

function keyEvidenceLabel(evidence, keyName, reference = false) {
  if (!keyName || evidence?.status === "unknown") return "Key unavailable";
  if (evidence?.status === "omr-detected") return `OMR-detected key: ${keyName}`;
  if (evidence?.status === "entered") return `Entered source key: ${keyName}`;
  return `${reference ? "Source-verified witness key" : "Source-verified key"}: ${keyName}`;
}

function tonicStepFromKey(key) {
  return parseKey(key)?.tonicStep || "C";
}

function shapeForEvent(event, sourceKey) {
  if (SHAPE_NAMES.has(event.shape)) return { name: event.shape, kind: "source" };
  if (!sourceKey || !event.step) return { name: "", kind: "unavailable" };
  const parsed = parseKey(sourceKey);
  if (!parsed) return { name: "", kind: "unavailable" };
  // Minor-key Sacred Harp notation uses the relative-major four-shape
  // spelling. For example, F# minor starts on the relative-major sixth
  // degree, so its tonic is a la shape rather than a new invented shape set.
  const relativeMajorStep = parsed.mode === "minor"
    ? DIATONIC_STEPS[(STEP_DIATONIC[parsed.tonicStep] + 2) % 7]
    : parsed.tonicStep;
  const degree = (STEP_DIATONIC[event.step] - STEP_DIATONIC[relativeMajorStep] + 7) % 7;
  return { name: SACRED_HARP_MAJOR_SHAPES[degree], kind: "derived" };
}

function partStaff(part, partIndex) {
  const declaredClefs = Object.values(part?.clefs || {});
  const eventClef = (part?.events || []).find((event) => event.clef)?.clef;
  const clef = eventClef || declaredClefs[0] || "";
  if (clef === "bass" || clef === "tenor" || clef === "alto" || clef === "treble") return clef;
  return partIndex < 2 ? "treble" : "bass";
}

function partClefGlyph(part, partIndex) {
  return partStaff(part, partIndex) === "bass" ? "𝄢" : "𝄞";
}

function pitchToMidi(event) {
  if (!event || event.rest || !event.step) return null;
  return 12 * (event.octave + 1) + STEP_SEMITONES[event.step] + (event.alter || 0);
}

function transposedNotation(event, sourceKey, targetKey, semitones) {
  if (!event || !event.step || !semitones) return { step: event.step, octave: event.octave, accidental: event.accidental };
  const midi = pitchToMidi(event);
  const source = parseKey(sourceKey);
  const target = parseKey(targetKey) || source;
  if (midi === null || !source || !target) return { step: event.step, octave: event.octave, accidental: event.accidental };
  const sourceDegree = (STEP_DIATONIC[event.step] - STEP_DIATONIC[source.tonicStep] + 7) % 7;
  const targetStep = DIATONIC_STEPS[(STEP_DIATONIC[target.tonicStep] + sourceDegree) % 7];
  const targetMidi = midi + semitones;
  const octave = Math.floor((targetMidi - STEP_SEMITONES[targetStep]) / 12) - 1;
  const naturalMidi = 12 * (octave + 1) + STEP_SEMITONES[targetStep];
  const alter = targetMidi - naturalMidi;
  const accidental = alter === 2 ? "double-sharp" : alter === 1 ? "sharp" : alter === -1 ? "flat" : alter === -2 ? "double-flat" : "";
  return { step: targetStep, octave, accidental };
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
  const pdfUrl = sourcePdfUrl(song);
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
  if (pdfUrl) return <div className="source-notation"><div className="source-notation-head"><span className="section-label">Source notation</span><span>PDF scan · not transposable</span></div><iframe title={`${song.songNo} ${song.title} source notation`} src={pdfUrl} loading="lazy" /><a href={pdfUrl} target="_blank" rel="noreferrer noopener">Open the source PDF <Icon name="external" size={16} /></a></div>;
  return <div className="source-notation source-notation-link" data-image-url={imageUrl}><div><span className="section-label">Source notation</span><h3>Notation is available on the authoritative source page</h3><p>This book publishes the page scan and recordings there; this atlas does not redraw it or invent a transposable score.</p></div><a href={pageUrl} target="_blank" rel="noreferrer noopener">Open source page <Icon name="external" size={16} /></a></div>;
}

function SourceRecording({ song, coverage }) {
  const tracks = coverage?.recordingTracks || [];
  const fullTrack = tracks.find((track) => track.isFullSong) || tracks.find((track) => /all\s*4\s*parts/i.test(track.title || ""));
  if (!fullTrack?.url) return null;
  const debutRecording = fullTrack.kind === "full-song-source-witness";
  const linkedTracks = tracks.filter((track) => track.url !== fullTrack.url);
  const sourcePages = coverage?.recordingSourcePages || [];
  return <div className="source-recording">
    <div className="source-notation-head"><span className="section-label">Reference audio</span><span>{debutRecording ? "Source witness · does not drive rendering" : "Four parts · does not drive rendering"}</span></div>
    <audio controls preload="none" src={fullTrack.url} aria-label={`${song.songNo} ${song.title} source recording`} />
    {debutRecording && <p className="source-recording-note">Recorded at the official 2025 debut singing. This is source audio only; it does not create or validate transposable notation.</p>}
    <div className="source-recording-links">{linkedTracks.map((track) => <a key={track.url} href={track.url} target="_blank" rel="noreferrer noopener">{track.title.replace(/^\d+\s*[-–]\s*/, "")} <Icon name="external" size={13} /></a>)}{sourcePages.filter((url) => /^https:\/\//.test(url)).map((url) => <a key={url} href={url} target="_blank" rel="noreferrer noopener" aria-label={`Open recording source at ${sourceHostLabel(url)}`}>Open recording source <Icon name="external" size={13} /></a>)}</div>
  </div>;
}

function accidentalGlyph(value) {
  return { sharp: "♯", flat: "♭", natural: "♮", "double-sharp": "𝄪", "double-flat": "𝄫", "quarter-flat": "♭" }[String(value || "").toLowerCase()] || "";
}

function Notehead({ shape, filled, x, y }) {
  if (shape === "fa") return <path d={`M${x - 5.6} ${y - 3.8} L${x + 5.6} ${y - 3.8} L${x} ${y + 4.2} Z`} className={filled ? "notehead filled" : "notehead"} />;
  if (shape === "la") return <rect x={x - 5.3} y={y - 3.5} width="10.6" height="7" rx="1" className={filled ? "notehead filled" : "notehead"} />;
  if (shape === "mi") return <path d={`M${x} ${y - 5} L${x + 5} ${y} L${x} ${y + 5} L${x - 5} ${y} Z`} className={filled ? "notehead filled" : "notehead"} />;
  return <ellipse cx={x} cy={y} rx="5.2" ry="3.5" transform={`rotate(-18 ${x} ${y})`} className={filled ? "notehead filled" : "notehead"} />;
}

function ScorePreview({ score, transpose, complete, sourceKey, targetKey, shapeSourceUrl, keyEvidence }) {
  const partRows = score?.parts || [];
  const timelineEnd = Math.max(...partRows.flatMap((part) => (part.events || []).map((event) => event.onset + event.beats)), 1);
  const scoreWidth = 760;
  const systemHeight = 214;
  const measuresPerSystem = 4;
  // Diatonic coordinates use C4 as zero. These are the bottom staff lines
  // for the clefs emitted by the MusicXML parser; tenor is not alto shifted
  // down, which was the source of the visibly misplaced tenor notes.
  const staffBottom = { treble: 2, alto: -4, tenor: -2, bass: -10 };
  const measureStarts = [];
  const seenMeasures = new Set();
  const sourceEvents = [...partRows.flatMap((part) => part.events || [])].sort((a, b) => a.onset - b.onset);
  for (const event of sourceEvents) {
    // MusicXML exports with multiple voices often revisit the same measure
    // after a backup. Keep one timeline entry per source measure so the
    // complete-song renderer does not duplicate barlines or React keys.
    const measureKey = String(event.measure || "");
    if (measureKey && !seenMeasures.has(measureKey)) {
      measureStarts.push({ measure: event.measure, onset: event.onset });
      seenMeasures.add(measureKey);
    }
  }
  const systemCount = Math.max(1, Math.ceil(measureStarts.length / measuresPerSystem));
  const scoreHeight = systemCount * systemHeight;
  const systemForEvent = (event) => {
    const measureIndex = measureStarts.findIndex((measure) => String(measure.measure) === String(event.measure));
    if (measureIndex >= 0) return Math.floor(measureIndex / measuresPerSystem);
    const preceding = measureStarts.reduce((index, measure, indexValue) => measure.onset <= event.onset ? indexValue : index, 0);
    return Math.min(Math.floor(preceding / measuresPerSystem), systemCount - 1);
  };
  const noteEvents = partRows.flatMap((part) => part.events || []).filter((event) => !event.rest && event.step);
  const shapeStats = noteEvents.reduce((stats, event) => {
    const shape = shapeForEvent(event, sourceKey);
    stats[shape.kind] += 1;
    return stats;
  }, { source: 0, derived: 0, unavailable: 0 });
  const shapeCaption = shapeStats.unavailable === 0
    ? shapeStats.derived > 0 ? "Sacred Harp four-shape rendering" : "Source-encoded shape-note rendering"
    : "Pitch/rhythm rendering · shapes unavailable";
  const displayedKey = targetKey ? keyLabel(`${targetKey} ${keyMode(sourceKey) || "major"}`) : keyLabel(sourceKey);
  const shapeNote = keyEvidence?.status === "omr-detected"
    ? "Shapes derived from an OMR-detected key; verify the key against the source before promotion."
    : shapeStats.derived > 0
      ? "Shapes derived from the recorded source key; the linked PDF remains authoritative."
      : shapeStats.source > 0
        ? "Shapes preserved from the source score."
        : "Shapes unavailable in the source; pitches and rhythms are preserved.";
  const sourceMeasureCount = Number(score?.sourceMeasureCount);
  const measureCaption = complete
    ? sourceMeasureCount && sourceMeasureCount !== measureStarts.length
      ? `${measureStarts.length} detected / ${sourceMeasureCount} source measures · draft view`
      : `${measureStarts.length ? `${measureStarts.length} measures · ` : ""}full-song view`
    : "loading full song";
  return <div className="score-frame">
    <div className="score-caption"><span>{complete ? `${shapeCaption} · ${measureCaption}` : `MusicXML source preview · ${measureCaption}`}</span><span>{displayedKey} · {score?.timeSignature || "time not encoded"}</span></div>
    <svg className="score-svg" style={{ width: "100%" }} viewBox={`0 0 ${scoreWidth} ${scoreHeight}`} role="img" aria-label={`${complete ? "Full" : "Preview of"} available source score with ${partRows.length} available parts`}>
      <rect x="0" y="0" width={scoreWidth} height={scoreHeight} fill="transparent" />
      {Array.from({ length: systemCount }, (_, systemIndex) => {
        const systemTop = systemIndex * systemHeight;
        const systemStart = measureStarts[systemIndex * measuresPerSystem]?.onset || 0;
        const systemEnd = measureStarts[(systemIndex + 1) * measuresPerSystem]?.onset || timelineEnd;
        const pixelsPerBeat = (scoreWidth - 88) / Math.max(systemEnd - systemStart, 1);
        const systemMeasures = measureStarts.slice(systemIndex * measuresPerSystem, (systemIndex + 1) * measuresPerSystem);
        return <g key={`system-${systemIndex}`} className="score-system">
          {partRows.map((part, partIndex) => {
            const base = systemTop + 22 + partIndex * 47;
            const events = (part.events || []).filter((event) => systemForEvent(event) === systemIndex);
            const staff = partStaff(part, partIndex);
            return <g key={`${systemIndex}-${part.name}`} className="score-part">
              {[0, 1, 2, 3, 4].map((line) => <line key={line} x1="58" y1={base + line * 4} x2={scoreWidth - 16} y2={base + line * 4} />)}
              <text x="8" y={base + 12} className="part-label">{part.name}</text>
              <text x="40" y={base + 14} className="clef-label">{partClefGlyph(part, partIndex)}</text>
              <line x1="58" y1={base} x2="58" y2={base + 16} className="barline" />
              {systemMeasures.slice(1).map((measure) => <line key={`${part.name}-measure-${measure.measure}`} x1={72 + (measure.onset - systemStart) * pixelsPerBeat} y1={base} x2={72 + (measure.onset - systemStart) * pixelsPerBeat} y2={base + 16} className="measure-line" />)}
              {events.map((event, eventIndex) => {
                const x = 72 + Math.max(0, event.onset - systemStart) * pixelsPerBeat;
                const midi = pitchToMidi(event);
                if (midi === null) return <path key={`${part.name}-${eventIndex}`} d={`M${x - 3} ${base + 8} q3 -6 6 0 q-3 6 -6 0`} className="rest-mark" />;
                const notation = transposedNotation(event, sourceKey, targetKey, transpose);
                const diatonic = 7 * (notation.octave - 4) + STEP_DIATONIC[notation.step];
                const relative = diatonic - staffBottom[staff];
                const y = base + 16 - relative * 2;
                const filled = !["whole", "half"].includes(String(event.type || "quarter").toLowerCase());
                const stemmed = !["whole"].includes(String(event.type || "quarter").toLowerCase());
                const flags = { eighth: 1, "16th": 2, "32nd": 3, "64th": 4 }[String(event.type || "").toLowerCase()] || 0;
                const accidental = accidentalGlyph(notation.accidental);
                const shape = shapeForEvent(event, sourceKey);
                return <g key={`${part.name}-${eventIndex}`} className="score-note">
                  <title>{shape.name ? `${shape.name} shape note` : "Shape note unavailable"}</title>
                  {accidental && <text x={x - 14} y={y + 4} className="accidental">{accidental}</text>}
                  <Notehead shape={shape.name || "round"} filled={filled} x={x} y={y} />
                  {stemmed && <line x1={x + 4.5} y1={y} x2={x + 4.5} y2={y - 14} />}
                  {flags > 0 && <path d={`M${x + 4.5} ${y - 14} q8 3 5 8${flags > 1 ? ` q8 3 5 8` : ""}`} className="flag" />}
                  {event.dots > 0 && <circle cx={x + (stemmed ? 11 : 8)} cy={y} r="1.4" className="duration-dot" />}
                </g>;
              })}
              <line x1={scoreWidth - 16} y1={base} x2={scoreWidth - 16} y2={base + 16} className="barline" />
            </g>;
          })}
          {systemIndex < systemCount - 1 && <line x1="0" y1={systemTop + systemHeight - 8} x2={scoreWidth} y2={systemTop + systemHeight - 8} className="system-divider" />}
        </g>;
      })}
    </svg>
    <p className="score-note">{shapeNote}{score?.playbackTransform?.finalChordRemoved && <> Final chord omitted from playback and transposition; source evidence is preserved.</>}{shapeSourceUrl && <> {" "}<a href={shapeSourceUrl} target="_blank" rel="noreferrer noopener">Open shape-source PDF <Icon name="external" size={13} /></a></>}</p>
  </div>;
}

function App() {
  const [corpus, setCorpus] = useState(null);
  const [corpusAttempt, setCorpusAttempt] = useState(0);
  const [humanReviewQueue, setHumanReviewQueue] = useState(null);
  const [humanReviewQueueError, setHumanReviewQueueError] = useState(false);
  const [humanReviewQueueAttempt, setHumanReviewQueueAttempt] = useState(0);
  const [bookId, setBookId] = useState(() => {
    try {
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
  const [selectedId, setSelectedId] = useState(() => {
    try {
      const savedBook = window.localStorage.getItem("sh-corpus-dashboard-book");
      const savedSelections = JSON.parse(window.localStorage.getItem("sh-corpus-dashboard-selected-tunes") || "{}");
      return BOOK_ORDER.includes(savedBook) && savedSelections && typeof savedSelections === "object" && typeof savedSelections[savedBook] === "string"
        ? savedSelections[savedBook]
        : "sh 45t — New Britain";
    } catch {
      return "sh 45t — New Britain";
    }
  });
  const [activeSection, setActiveSection] = useState("Library");
  const [targetKey, setTargetKey] = useState("");
  const [activeParts, setActiveParts] = useState([]);
  const [playing, setPlaying] = useState(false);
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
  const audioRef = useRef({ context: null, master: null, nodes: [], stopTimer: null });
  const toastTimerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setCorpus(null);
    fetch("/corpus.json")
      .then((response) => {
        if (!response.ok) throw new Error(`Corpus request failed: ${response.status}`);
        return response.json();
      })
      .then((data) => { if (!cancelled) setCorpus(data); })
      .catch(() => { if (!cancelled) setCorpus({ error: true }); });
    return () => { cancelled = true; };
  }, [corpusAttempt]);

  useEffect(() => {
    let cancelled = false;
    setHumanReviewQueueError(false);
    fetch("/human-review-queue.json")
      .then((response) => {
        if (!response.ok) throw new Error(`Review queue request failed: ${response.status}`);
        return response.json();
      })
      .then((data) => { if (!cancelled) setHumanReviewQueue(data); })
      .catch(() => {
        if (!cancelled) {
          setHumanReviewQueue(null);
          setHumanReviewQueueError(true);
        }
      });
    return () => { cancelled = true; };
  }, [humanReviewQueueAttempt]);

  useEffect(() => {
    try {
      window.localStorage.setItem("sh-corpus-dashboard-source-keys", JSON.stringify(sourceKeyOverrides));
    } catch {
      // Source-key choices remain available for this session when storage is unavailable.
    }
  }, [sourceKeyOverrides]);

  const book = corpus?.books?.[bookId];
  const bookCoverage = corpus?.coverage?.byBook?.[bookId] || { records: 0, localScoreRecords: 0 };
  const transposableCount = bookCoverage.transposableRecords || 0;
  const coverageSummary = `${formatCount(bookCoverage.transposableLocalScoreRecords || 0)} exact scores, ${formatCount(bookCoverage.transposableReferenceRecords || 0)} reference witnesses, and ${formatCount(bookCoverage.transposableDraftRecords || 0)} review drafts are transposable; ${formatCount(bookCoverage.keyUnknownStructuredRecords || 0)} structured records remain key-unknown`;

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
  const selectedSong = corpus?.songs ? corpus.songs.find((song) => song.id === selectedId && song.books.includes(bookId)) || getBookSongs(corpus, bookId)[0] : undefined;

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

  const selectedScorePreview = getBookScore(selectedSong, bookId);
  const selectedReferenceScore = getBookReferenceScore(selectedSong, bookId);
  const selectedDraftScore = getBookDraftScore(selectedSong, bookId);
  const activeScorePreview = selectedScorePreview || selectedReferenceScore || selectedDraftScore;
  const referenceScoreActive = !selectedScorePreview && Boolean(selectedReferenceScore);
  const draftScoreActive = !selectedScorePreview && !selectedReferenceScore && Boolean(selectedDraftScore);
  const selectedMetadata = getBookMetadata(selectedSong, bookId);
  const selectedCoverage = selectedSong?.sourceCoverageByBook?.[bookId];
  const sourceKeyOverrideId = selectedSong ? `${bookId}/${selectedSong.songNo}` : "";
  const enteredSourceKey = sourceKeyOverrides[sourceKeyOverrideId] || "";
  // Transposition follows the loaded witness itself. A score key wins over
  // catalog metadata; metadata is only a fallback when the score does not
  // encode a valid key. If neither is recorded, the user may enter the key
  // printed in the linked source; it remains separate from source metadata.
  const resolvedKey = keyContext(activeScorePreview, selectedMetadata, enteredSourceKey);
  const sourceKeyValue = resolvedKey.value;
  const shapeSourceKey = sourceKeyValue;
  const sourceKeyName = keyLabel(sourceKeyValue);
  const sourceKeyLabel = keyEvidenceLabel(resolvedKey.evidence, sourceKeyName, referenceScoreActive);
  const sourceMode = keyMode(sourceKeyValue) || "major";
  const transpose = targetKey ? ((ROOT_PITCH[targetKey] - rootFromKey(sourceKeyValue)) + 12) % 12 : 0;
  const signedTranspose = transpose > 6 ? transpose - 12 : transpose;
  const sourceUrls = [...new Set([...(selectedMetadata?.sourceUrl ? [selectedMetadata.sourceUrl] : []), ...(selectedMetadata?.sourceUrls || []), ...(selectedSong?.urls || [])])].slice(0, 6);
  const scoreRef = activeScorePreview?.scoreRef || "";
  const selectedScore = fullScore?.sourceUrl === activeScorePreview?.sourceUrl ? fullScore : activeScorePreview;
  const scoreLoaded = Boolean(activeScorePreview && fullScore?.sourceUrl === activeScorePreview.sourceUrl);
  const hasPitchedEvents = Boolean(selectedScore?.parts?.some((part) => (part.events || []).some((event) => !event.rest && event.step)));
  const canTranspose = Boolean(scoreLoaded && hasPitchedEvents && parseKey(sourceKeyValue));
  const scoreBadgeLabel = canTranspose
    ? referenceScoreActive ? "Transposable reference" : draftScoreActive ? "Transposable draft" : "Transposable score"
    : referenceScoreActive ? "Structured reference" : draftScoreActive ? "Review draft" : "Structured score";
  const alternateEdition = bookId === "sh2025" && getBookScore(selectedSong, "sh1991") ? "sh1991" : bookId === "sh1991" && getBookScore(selectedSong, "sh2025") ? "sh2025" : "";
  const editionReconciliation = selectedSong?.editionReconciliation;
  const referenceSourceLabel = activeScorePreview?.provenance?.sourceEdition === "sh1991" ? "Sacred Harp 1991" : "another edition/source";
  const reviewDraft = humanReviewQueue?.reviewNow?.find((item) => item.queueId === `${bookId}/${selectedSong?.songNo || ""}`);

  const results = useMemo(() => {
    if (!corpus?.songs) return [];
    const normalizedQuery = normalize(query);
    const songs = getBookSongs(corpus, bookId).filter((song) => {
      if (activeSection === "Practice") return getBookScore(song, bookId) || getBookReferenceScore(song, bookId) || getBookDraftScore(song, bookId);
      if (activeSection === "Sources") return isSourceRecord(song, bookId);
      return true;
    });
    if (!normalizedQuery) {
      const visibleSongs = songs.slice(0, 80);
      const selectedVisibleSong = songs.find((song) => song.id === selectedId);
      return selectedVisibleSong && !visibleSongs.some((song) => song.id === selectedVisibleSong.id)
        ? [...visibleSongs.slice(0, 79), selectedVisibleSong]
        : visibleSongs;
    }
    return songs.filter((song) => { const metadata = getBookMetadata(song, bookId) || {}; const coverage = song.sourceCoverageByBook?.[bookId] || {}; const sourceTerms = [metadata.sourceUrl, ...(metadata.sourceUrls || []), ...(coverage.sourceUrls || []), coverage.editionEvidenceUrl, coverage.sourceImageUrl]; return normalize([song.songNo, song.title, song.rawFirstLine, song.textKey, metadata.composer, metadata.lyricist, coverage.status, coverage.nextAction, ...sourceTerms].join(" ")).includes(normalizedQuery); }).slice(0, 80);
  }, [corpus, bookId, query, activeSection, selectedId]);

  useEffect(() => {
    if (results.length && selectedSong && !results.some((song) => song.id === selectedSong.id)) {
      setSelectedId(results[0].id);
    }
  }, [results, selectedSong?.id]);

  useEffect(() => {
    let cancelled = false;
    setFullScore(null);
    setScoreLoadError(false);
    if (!scoreRef) return () => { cancelled = true; };
    fetch(scoreRef)
      .then((response) => {
        if (!response.ok) throw new Error(`Score request failed: ${response.status}`);
        return response.json();
      })
      .then((score) => { if (!cancelled) setFullScore(score); })
      .catch(() => { if (!cancelled) { setFullScore(null); setScoreLoadError(true); } });
    return () => { cancelled = true; };
  }, [scoreRef, scoreLoadAttempt]);

  useEffect(() => {
    if (!selectedSong) return;
    setTargetKey("");
    setActiveParts(activeScorePreview?.parts?.map((part) => part.name) || []);
    stopAudio("Playback stopped because the selected tune changed.");
  }, [selectedId, bookId, scoreRef]);

  if (!corpus) return <div className="loading-screen" role="status" aria-live="polite">Loading the local atlas…</div>;
  if (corpus.error) return <div className="loading-screen" role="alert"><Icon name="info" size={22} /><p>The local corpus bundle could not be loaded. Serve the project through its static host and try again.</p><button className="text-button" type="button" onClick={() => setCorpusAttempt((attempt) => attempt + 1)}>Retry loading</button></div>;

  function stopAudio(notice = "") {
    const audio = audioRef.current;
    const wasPlaying = audio.nodes.length > 0 || Boolean(audio.master) || Boolean(audio.stopTimer);
    if (audio.stopTimer) {
      window.clearTimeout(audio.stopTimer);
      audio.stopTimer = null;
    }
    audio.nodes.forEach((node) => { try { node.stop(); } catch {} });
    audio.nodes = [];
    if (audio.master) {
      try { audio.master.disconnect(); } catch {}
      audio.master = null;
    }
    setPlaying(false);
    if (notice && wasPlaying) setPlaybackNotice(notice);
  }

  async function playAvailableParts() {
    if (!scoreLoaded || !selectedScore || !activeParts.length) return;
    setPlaybackNotice("");
    stopAudio();
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
      if (context.state !== "running") {
        showToast("Audio is unavailable until the browser allows playback.");
        return;
      }
    } catch {
      showToast("Audio could not start. Check the browser's audio permission.");
      return;
    }
    const now = context.currentTime + 0.08;
    const beatSeconds = 0.34;
    const nodes = [];
    const parts = selectedScore.parts.filter((part) => activeParts.includes(part.name));
    const master = context.createGain();
    master.gain.setValueAtTime(0.78, now);
    master.connect(context.destination);
    audioRef.current.master = master;
    try {
      parts.forEach((part, partIndex) => {
        (part.events || []).forEach((event) => {
          if (event.rest) return;
          const sourceMidi = pitchToMidi(event);
          const onset = Number(event.onset);
          const beats = Number(event.beats);
          if (sourceMidi === null || !Number.isFinite(sourceMidi) || !Number.isFinite(onset) || !Number.isFinite(beats) || beats <= 0) return;
          const midi = sourceMidi + signedTranspose;
          const oscillator = context.createOscillator();
          const gain = context.createGain();
          const pan = context.createStereoPanner ? context.createStereoPanner() : null;
          oscillator.type = partIndex % 2 ? "triangle" : "sine";
          oscillator.frequency.value = 440 * Math.pow(2, (midi - 69) / 12);
          const start = Math.max(context.currentTime + 0.02, now + onset * beatSeconds);
          const duration = Math.max(0.12, beats * beatSeconds * 0.9);
          const noteLevel = Math.min(0.18, 0.72 / Math.max(parts.length, 1));
          gain.gain.setValueAtTime(0, start);
          gain.gain.linearRampToValueAtTime(noteLevel, start + 0.025);
          gain.gain.setTargetAtTime(0, start + duration * 0.72, 0.08);
          oscillator.connect(gain);
          if (pan) { pan.pan.value = (partIndex - (parts.length - 1) / 2) * 0.22; gain.connect(pan); pan.connect(master); } else gain.connect(master);
          oscillator.start(start);
          oscillator.stop(start + duration + 0.15);
          nodes.push(oscillator);
        });
      });
    } catch (error) {
      stopAudio();
      console.error("Sacred Harp audio scheduling failed", error);
      showToast("Audio could not be scheduled for this score.");
      return;
    }
    if (!nodes.length) {
      stopAudio();
      showToast("This score has no playable pitched events.");
      return;
    }
    audioRef.current.nodes = nodes;
    setPlaying(true);
    const lastEvent = Math.max(...parts.flatMap((part) => (part.events || []).map((event) => Number(event.onset) + Number(event.beats)).filter(Number.isFinite)), 1);
    const playbackDurationMs = (lastEvent * beatSeconds + 0.5) * 1000;
    audioRef.current.stopTimer = window.setTimeout(() => { if (audioRef.current.nodes === nodes) stopAudio(); }, playbackDurationMs);
  }

  function handleBookChange(nextBookId) {
    setBookId(nextBookId);
    const next = getBookSongs(corpus, nextBookId)[0];
    if (next) setSelectedId(next.id);
  }

  function toggleTheme() {
    setMode((current) => current === "dark" ? "light" : "dark");
  }

  function togglePart(name) {
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
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    setToast(message);
    toastTimerRef.current = window.setTimeout(() => {
      setToast("");
      toastTimerRef.current = null;
    }, 2600);
  }

  const bookSongs = getBookSongs(corpus, bookId);
  const sourceRecordCount = bookSongs.filter((song) => isSourceRecord(song, bookId)).length;
  const resultSummary = activeSection === "Sources"
    ? `${formatCount(results.length)} shown · ${formatCount(sourceRecordCount)} source records`
    : `${formatCount(results.length)} shown · ${formatCount(bookSongs.length)} tunes`;

  return <div className="app-shell">
    <a className="skip-link" href="#selected-tune-details">Skip to selected tune details</a>
    <header className="atlas-header">
      <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">◇</div><h1>Shape-Note Atlas</h1></div>
      <nav className="primary-nav" aria-label="Primary navigation">
        {[{ label: "Library", icon: "book" }, { label: "Practice", icon: "practice" }, { label: "Sources", icon: "source" }].map((item) => <button key={item.label} className={`nav-item ${activeSection === item.label ? "active" : ""}`} aria-current={activeSection === item.label ? "page" : undefined} onClick={() => setActiveSection(item.label)}><Icon name={item.icon} /><span>{item.label}</span></button>)}
      </nav>
      <div className="header-controls">
        <label className="book-select-wrap header-book-picker" htmlFor="book-select"><span className="sr-only">Tune book</span><Icon name="book" size={18} /><select id="book-select" aria-label="Tune book" value={bookId} onChange={(event) => handleBookChange(event.target.value)}>{BOOK_ORDER.filter((id) => corpus.books[id]).map((id) => <option key={id} value={id}>{corpus.books[id].label}</option>)}</select><span className="select-chevron">⌄</span></label>
        <span className="coverage-summary" title={coverageSummary}><span aria-hidden="true">{formatCount(transposableCount)} transposable · {formatCount(bookCoverage.records)} tunes</span><span className="sr-only">{coverageSummary}</span></span>
        <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${mode === "dark" ? "light" : "dark"} mode`}>{mode === "dark" ? "Light" : "Dark"}</button>
      </div>
    </header>

    <main className="workspace">
      <section className="results-column" aria-label="Tune search results">
        <div className="results-head"><div className="search-box"><Icon name="search" size={20} /><input data-testid="tune-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tunes, pages, first lines, or sources" aria-label="Search tune, page, first line, or source metadata" />{query && <button className="clear-search" onClick={() => setQuery("")} aria-label="Clear search">×</button>}</div><div className="results-kicker">{activeSection}</div><div className="results-summary" aria-live="polite" aria-atomic="true">{resultSummary}</div></div>
        <div className="results-list">
        {results.length ? results.map((song) => { const sourceStatus = sourceRowStatus(song, bookId); const rowStatus = activeSection === "Sources" ? <span className="tiny-status source-status"><Icon name={sourceStatus.icon} size={13} />{sourceStatus.label}</span> : getBookScore(song, bookId) ? <span className="tiny-status"><Icon name="check" size={13} />score</span> : getBookReferenceScore(song, bookId) ? <span className="tiny-status"><Icon name="check" size={13} />reference</span> : getBookDraftScore(song, bookId) ? <span className="tiny-status draft-status">draft</span> : <span className="tiny-status muted"><Icon name="info" size={13} />metadata</span>; return <button key={song.id} className={`result-row ${song.id === selectedSong?.id ? "selected" : ""}`} aria-pressed={song.id === selectedSong?.id} onClick={() => setSelectedId(song.id)}><div className="result-copy"><span className="result-number">{song.songNo}</span><strong>{song.title}</strong><span>{song.rawFirstLine || song.textKey}</span></div><div className="result-status">{rowStatus}<Icon name="chevron" size={17} /></div></button>; }) : <div className="empty-results"><Icon name="search" size={23} /><h3>No matching records</h3><p>{activeSection === "Sources" ? "This edition has no source follow-up records." : "Try a tune title, page number, or first line."}</p></div>}
        </div>
      </section>

      <section className="detail-column" id="selected-tune-details" aria-label="Selected tune details" tabIndex="-1">
        {selectedSong ? <>
          <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">Selected tune: {selectedSong.songNo} — {selectedSong.title}</div>
          <div className="detail-header"><div><div className="detail-overline">{book.label} · page {selectedSong.songNo}</div><h2>{selectedSong.songNo} — {selectedSong.title}</h2></div><button className="icon-button" aria-label="Show source preservation note" onClick={() => showToast("Source links and score data are preserved locally.")}><Icon name="info" size={20} /></button></div>
          <div className="detail-tags">{selectedScore ? <span className={`tag ${canTranspose ? referenceScoreActive ? "reference-tag" : draftScoreActive ? "draft-tag" : "available" : "unavailable"}`}><Icon name={canTranspose ? "check" : "info"} size={14} />{scoreBadgeLabel}</span> : selectedCoverage?.status === "transcription-blocked" ? <span className="tag unavailable"><Icon name="info" size={14} />Transcription blocked</span> : sourcePdfUrl(selectedSong) || sourcePageUrl(selectedSong, bookId) ? <span className="tag available"><Icon name="check" size={14} />Source scan</span> : selectedCoverage?.status === "source-reference" ? <span className="tag available"><Icon name="check" size={14} />Source reference</span> : <span className="tag unavailable"><Icon name="info" size={14} />Metadata only</span>}{(selectedScore || sourceKeyValue || draftScoreActive) && <span className="tag key-tag">{sourceKeyValue ? sourceKeyLabel : "Key unavailable"}</span>}{bookId === "sh2025" && selectedMetadata?.editionStatus === "added-in-2025" && <span className="tag edition-new-tag">New in 2025</span>}{editionReconciliation && <span className="tag edition-tag">{editionReconciliation.status === "change-flagged" ? "1991 / 2025 text differs" : "Shared by 1991 / 2025"}</span>}</div>
          <div className="first-line"><span className="section-label">First line</span><p>{selectedSong.rawFirstLine || "No first line recorded in the local source."}</p></div>
          {humanReviewQueueError && selectedCoverage && selectedCoverage.status !== "structured-score" && <div className="source-coverage-note"><Icon name="info" size={18} /><span role="status"><strong>Review status unavailable.</strong> The local human-review queue could not be loaded. Source coverage and score data are unchanged; reload when the local server is available.</span><button className="text-button" type="button" onClick={() => setHumanReviewQueueAttempt((attempt) => attempt + 1)}>Retry</button></div>}
          {selectedScore ? <>
            {referenceScoreActive && <div className="reference-score-note"><Icon name="info" size={18} /><span>This is a transposable reference witness from {referenceSourceLabel}. It is shown for practice, but it is not being presented as the {book.label} engraving.</span></div>}
            {draftScoreActive && <div className="draft-score-note"><Icon name="info" size={18} /><span>This is an unverified OMR transcription draft. It is playable and transposable for review, but it is not the {book.label} engraving and does not count as verified coverage. <a href="/human-review-queue.json" target="_blank" rel="noreferrer noopener">Open review queue <Icon name="external" size={13} /></a></span></div>}
            {selectedCoverage?.status === "transcription-blocked" && <div className="source-coverage-note"><Icon name="info" size={18} /><span><strong>Source coverage blocked.</strong> {coverageNextStep(selectedCoverage)} This review draft remains isolated until an authorized source is acquired.</span></div>}
            <div className="parts-heading"><span className="section-label">Available parts</span><span className="parts-count">{activeParts.length} of {selectedScore.parts.length} selected</span></div>
            <div className="part-toggles" role="group" aria-label="Available parts">{selectedScore.parts.map((part) => <button key={part.name} className={`part-toggle ${activeParts.includes(part.name) ? "selected" : ""}`} aria-pressed={activeParts.includes(part.name)} onClick={() => togglePart(part.name)}><span className="part-clef">{part.name === "Bass" || part.name === "Tenor" ? "𝄢" : "𝄞"}</span><span>{part.name}</span><span className="part-check"><Icon name="check" size={13} /></span></button>)}</div>
            <ScorePreview score={selectedScore} transpose={signedTranspose} complete={scoreLoaded} sourceKey={shapeSourceKey} targetKey={targetKey} shapeSourceUrl={shapeSourcePdfUrl(activeScorePreview)} keyEvidence={resolvedKey.evidence} />
            {(!sourceKeyValue || resolvedKey.evidence?.status === "entered") && <div className="source-key-picker"><div><span className="section-label">{sourceKeyValue ? "Entered source key" : "Source key required"}</span><p>{sourceKeyValue ? "Change this if the key printed in the source differs." : "Choose the key printed in this source to unlock pitch-accurate transposition."}</p></div><label className="key-select-wrap"><span className="sr-only">Source key</span><select aria-label="Source key" value={enteredSourceKey} onChange={(event) => setEnteredSourceKey(event.target.value)}><option value="">Choose source key…</option>{["major", "minor"].flatMap((mode) => KEY_NAMES.map((key) => <option key={`${key}:${mode}`} value={`${key}:${mode}`}>{key} {mode}</option>))}</select><span className="select-chevron">⌄</span></label></div>}
            <div className="transport-row"><div className="playback-controls"><button className="primary-button" onClick={playing ? () => stopAudio() : scoreLoadError ? () => setScoreLoadAttempt((attempt) => attempt + 1) : playAvailableParts} disabled={scoreLoadError ? false : !scoreLoaded || !activeParts.length}>{playing ? <Icon name="stop" size={14} /> : <Icon name="play" size={15} />}{playing ? "Stop" : scoreLoadError ? "Retry loading" : scoreLoaded ? "Play song" : "Loading…"}</button></div><div className="transpose-controls"><button className="secondary-button" title="Transpose down one semitone" aria-label="Transpose down one semitone" onClick={() => nudgeTranspose(-1)} disabled={!canTranspose}><Icon name="arrowDown" size={16} />Down</button><label className="key-select-wrap"><span className="sr-only">Target key</span><select aria-label="Target key" value={targetKey} onChange={(event) => { stopAudio("Playback stopped because the target key changed."); setTargetKey(event.target.value); }} disabled={!canTranspose}><option value="">{sourceKeyName}</option>{KEY_NAMES.filter((key) => key !== sourceKeyName.split(" ")[0]).map((key) => <option key={key} value={key}>{key} {sourceMode}</option>)}</select><span className="select-chevron">⌄</span></label><button className="secondary-button" title="Transpose up one semitone" aria-label="Transpose up one semitone" onClick={() => nudgeTranspose(1)} disabled={!canTranspose}><Icon name="arrowUp" size={16} />Up</button></div></div>
            {scoreRef && !scoreLoaded && !scoreLoadError && <div className="sr-only" role="status" aria-live="polite">Loading the structured score…</div>}
            {scoreLoadError && <div className="score-load-error" role="alert"><Icon name="info" size={16} /><span>The full score could not be loaded. Check the local server, then retry.</span></div>}
            {signedTranspose !== 0 && <div className="transposition-note" role="status" aria-live="polite" aria-atomic="true"><span>Transposed {signedTranspose > 0 ? "+" : "−"}{Math.abs(signedTranspose)} semitone{Math.abs(signedTranspose) === 1 ? "" : "s"} from {sourceKeyName}</span></div>}
            <div className="structured-score-status"><Icon name={draftScoreActive || !canTranspose ? "info" : "check"} size={16} /><span>{draftScoreActive ? "Draft loaded for review playback and transposition; source comparison is still required." : "Structured source loaded for playback."} {sourceKeyValue ? `${sourceKeyLabel}.` : "Choose the source key above to enable transposition."}</span></div>
            {draftScoreActive && <SourceRecording song={selectedSong} coverage={selectedCoverage} />}
          </> : <><div className="missing-score"><Icon name="info" size={23} /><div><h3>No transposable score file for this record</h3><p>The atlas preserves the exact source link or scan instead of synthesizing notation where structured score data is absent.</p>{selectedCoverage && <p className="edition-note"><strong>{coverageLabel(selectedCoverage)}.</strong> {coverageNextStep(selectedCoverage)}</p>}{selectedCoverage?.editionStatus === "added-in-2025" && <p className="edition-note"><strong>New in 2025.</strong> This page is on the publisher's additions list and has no verified 2025 MusicXML yet. <a href={selectedCoverage.editionEvidenceUrl} target="_blank" rel="noreferrer noopener">View the source list <Icon name="external" size={13} /></a></p>}{reviewDraft && <p className="edition-note"><strong>Draft ready for human review.</strong> {reviewDraft.draftSummary.parts} parts, {Object.values(reviewDraft.draftSummary.measuresByPart)[0] || "unknown"} measures per part. It is not playable or transposable until the source comparison is complete. <a href="/human-review-queue.json" target="_blank" rel="noreferrer noopener">Open review queue <Icon name="external" size={13} /></a></p>}{alternateEdition && <p className="edition-note">A verified {alternateEdition === "sh1991" ? "1991" : "2025"}-edition score is available for this shared tune, but it is not being mislabeled as a {bookId === "sh2025" ? "2025" : "1991"} score.</p>}{alternateEdition && <button className="text-button" onClick={() => { setBookId(alternateEdition); setSelectedId(selectedSong.id); }}>Open the verified {alternateEdition === "sh1991" ? "1991" : "2025"} score</button>}</div></div><SourceNotation song={selectedSong} bookId={bookId} /><SourceRecording song={selectedSong} coverage={selectedCoverage} /></>}
          <div className="source-strip"><div><span className="section-label">Source</span><span>{selectedMetadata?.sourceUrl ? `${book.label}, page ${selectedSong.songNo}` : "Local corpus record"}</span></div><div className="source-actions">{sourceUrls.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer noopener" aria-label={`Open source record at ${sourceDestinationLabel(url)}`}>Open source record <Icon name="external" size={16} /></a>)}{activeScorePreview && shapeSourcePdfUrl(activeScorePreview) && <a href={shapeSourcePdfUrl(activeScorePreview)} target="_blank" rel="noreferrer noopener">Open shape-source PDF <Icon name="external" size={16} /></a>}</div></div>
          <div className="detail-footer"><ShapeLegend /></div>
        </> : <div className="missing-score"><Icon name="info" size={23} /><div><h3>Select a tune to begin</h3><p>Search the local atlas by page, title, or first line.</p></div></div>}
      </section>
    </main>
    {toast && <div className="toast" role="status"><Icon name="check" size={16} />{toast}</div>}
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{playbackNotice}</div>
  </div>;
}

createRoot(document.getElementById("root")).render(<App />);
