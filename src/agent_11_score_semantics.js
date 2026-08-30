/**
 * Rendering/playback adapter for the agent-11 MusicXML semantic contract.
 *
 * This module is intentionally pure and unconnected to the current dashboard
 * entry point.  It gives a future renderer one honest boundary: encoded
 * repeats may expand into an explicit measure sequence; unavailable or
 * blocked semantics stay linear and carry their reason to the UI.
 */

export function lyricForEvent(part, eventIndex, lyricNumber = "") {
  return (part?.lyrics || []).filter((lyric) => (
    lyric.eventIndex === eventIndex && (!lyricNumber || lyric.number === lyricNumber)
  ));
}

export function barlinesForMeasure(part, measureNumber) {
  return (part?.barlines || []).filter((barline) => String(barline.measure) === String(measureNumber));
}

export function semanticAvailabilityLabel(availability, field) {
  const status = availability?.[field]?.status || "unavailable";
  if (status === "encoded") return "Source-encoded";
  if (status === "blocked") return "Unavailable · source evidence incomplete";
  return "Unavailable · not encoded in source";
}

export function playbackEvents(events, playback) {
  const sourceEvents = Array.isArray(events) ? events : [];
  if (playback?.status !== "encoded" || playback?.safeToApply !== true) {
    return {
      events: sourceEvents,
      repeated: false,
      status: playback?.status || "unavailable",
      reason: playback?.reason || "source playback semantics are unavailable",
    };
  }

  const byMeasure = new Map();
  sourceEvents.forEach((event) => {
    const key = String(event.measure);
    if (!byMeasure.has(key)) byMeasure.set(key, []);
    byMeasure.get(key).push(event);
  });
  const expanded = [];
  (playback.measureSequence || []).forEach((measure) => {
    (byMeasure.get(String(measure)) || []).forEach((event) => expanded.push(event));
  });
  return {
    events: expanded,
    repeated: expanded.length !== sourceEvents.length,
    status: "encoded",
    reason: playback.reason,
  };
}

export function scoreSemanticSummary(score) {
  const availability = score?.availability || {};
  return {
    lyrics: semanticAvailabilityLabel(availability, "lyrics"),
    repeats: semanticAvailabilityLabel(availability, "repeats"),
    numberedEndings: semanticAvailabilityLabel(availability, "numberedEndings"),
    editorialMarkings: semanticAvailabilityLabel(availability, "editorialMarkings"),
    playback: score?.playback?.status === "encoded"
      ? "Explicit repeat/ending playback"
      : "Linear source-order playback",
  };
}
