const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function requireValue(condition, path) {
  if (!condition) throw new Error(`Incompatible full score: ${path}`);
}
function optionalRecords(value, path) {
  if (value == null) return;
  requireValue(Array.isArray(value) && value.every(record), path);
}
function playback(value, path) {
  if (value == null) return;
  requireValue(record(value), path);
  if (value.measureSequence != null) requireValue(Array.isArray(value.measureSequence), `${path}.measureSequence`);
}

// This boundary protects reader collections and requested witness identity.
// Pitch, timing, musical completeness and source accuracy retain their existing
// engraving/quarantine checks; empty and rest-only scores remain valid here.
export function validateScore(score, expectedSourceUrl) {
  requireValue(record(score), 'root must be an object');
  requireValue(typeof expectedSourceUrl === 'string' && expectedSourceUrl.length > 0
    && score.sourceUrl === expectedSourceUrl, 'sourceUrl must match the requested witness');
  requireValue(Array.isArray(score.parts), 'parts must be an array');
  if (score.timeSignature != null) requireValue(typeof score.timeSignature === 'string', 'timeSignature');
  optionalRecords(score.lyrics, 'lyrics');
  playback(score.playback, 'playback');
  if (score.semanticContract != null) {
    requireValue(record(score.semanticContract), 'semanticContract');
    playback(score.semanticContract.playback, 'semanticContract.playback');
  }
  score.parts.forEach((part, index) => {
    const path = `parts[${index}]`;
    requireValue(record(part) && typeof part.name === 'string' && part.name.length > 0, path);
    requireValue(Array.isArray(part.events) && part.events.every(record), `${path}.events`);
    for (const field of ['lyrics', 'barlines', 'measureSemantics']) optionalRecords(part[field], `${path}.${field}`);
    for (const measure of part.measureSemantics || []) optionalRecords(measure.barlines, `${path}.measureSemantics.barlines`);
    part.events.forEach((event, eventIndex) => {
      for (const field of ['lyrics', 'editorialMarkings']) optionalRecords(event[field], `${path}.events[${eventIndex}].${field}`);
    });
  });
  return score;
}
