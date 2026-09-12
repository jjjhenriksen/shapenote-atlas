// Preserve literal MusicXML geometry independently of key/mode authority.
// A normal oval is a round notehead, not evidence for the sol syllable.
const GLYPHS = { fa: 'fa', sol: 'sol', la: 'la', mi: 'mi', triangle: 'fa', square: 'la', diamond: 'mi', normal: 'round' };

export function sourceNoteheadEvidence(event) {
  const encoded = event?.notehead || event?.shape;
  if (!encoded) return null;
  const value = String(encoded).toLowerCase();
  const name = Object.hasOwn(GLYPHS, value) ? GLYPHS[value] : undefined;
  return name ? { name, kind: 'source' } : { name: '', kind: 'unavailable' };
}

export function noteheadFilled(event) {
  return typeof event?.noteheadFilled === 'boolean'
    ? event.noteheadFilled
    : !['whole', 'half'].includes(String(event?.type || 'quarter').toLowerCase());
}
