# Source-faithful notation

Tracking: [#37](https://github.com/jjjhenriksen/shapenote-atlas/issues/37).

Atlas adopts Hollow Square's architecture—structured source → MusicXML →
OpenSheetMusicDisplay SVG—rather than its simplified MIDI-to-pitch game adapter.
The pure `scoreToMusicXml` boundary preserves written pitch/alter/octave, encoded
C/G/F clefs, voices/staves, source measure timing and source/derived notehead
separation. Conversion does not promote a draft, authorize playback, or mutate
source assets. Missing keys do not turn into fabricated C-major evidence.
Unsupported clefs and invalid timing/pitches fail explicitly.

This first stack layer is not wired into the reader. Later layers add encoded
lyrics, repeat/endings and visual ties, then the reader integration; source
availability and provenance warnings remain authoritative. Existing publication
and playback quarantine gates are not replaced by successful engraving.

Quarter-note durations use 1000 divisions, matching the parser's three-decimal
beat contract. Empty measures retain forward timing rather than invented rests.
Independent voices use MusicXML backup/forward and simultaneous notes use chords.
The original event-index mapping remains available for lyric attachment, even
when ambiguous OMR collisions are suppressed in review views.
