// Pure pitch spelling shared by the score renderer and its regression checks.
export const ROOT_PITCH = { C: 0, "B#": 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4, "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11 };
export const STEP_SEMITONES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
export const STEP_DIATONIC = { C: 0, D: 1, E: 2, F: 3, G: 4, A: 5, B: 6 };
export const DIATONIC_STEPS = ["C", "D", "E", "F", "G", "A", "B"];

export function parseKey(key) {
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


export function pitchToMidi(event) {
  if (!event || event.rest || !event.step) return null;
  return 12 * (event.octave + 1) + STEP_SEMITONES[event.step] + (event.alter || 0);
}


export function transposedNotation(event, sourceKey, targetKey, semitones) {
  if (!event || !event.step || !semitones) return { step: event.step, octave: event.octave, accidental: event.accidental };
  const midi = pitchToMidi(event);
  const source = parseKey(sourceKey);
  const target = parseKey(targetKey) || source;
  if (midi === null || !source || !target) return { step: event.step, octave: event.octave, accidental: event.accidental };
  const sourceDegree = (STEP_DIATONIC[event.step] - STEP_DIATONIC[source.tonicStep] + 7) % 7;
  const targetStep = DIATONIC_STEPS[(STEP_DIATONIC[target.tonicStep] + sourceDegree) % 7];
  const targetMidi = midi + semitones;
  // Flats lie below their natural note. Flooring would pick the previous
  // octave and turn a flat into +11 semitones (which has no accidental glyph).
  const octave = Math.round((targetMidi - STEP_SEMITONES[targetStep]) / 12) - 1;
  const naturalMidi = 12 * (octave + 1) + STEP_SEMITONES[targetStep];
  const alter = targetMidi - naturalMidi;
  const accidental = alter === 2 ? "double-sharp" : alter === 1 ? "sharp" : alter === -1 ? "flat" : alter === -2 ? "double-flat" : "";
  return { step: targetStep, octave, accidental };
}

