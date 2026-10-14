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

## Reader integration

`ScoreEngraving` lazy-loads pinned OpenSheetMusicDisplay 2.2.1 (BSD-3-Clause;
see `node_modules/opensheetmusicdisplay/LICENSE`). It uses SVG engraving like
Hollow Square, but enables Atlas's encoded lyrics, C clefs, repeats/endings,
visual ties and slurs. Lyrics receive explicit spacing instead of hand-positioned
staff rows. No complete underlying XML or local filesystem provenance is exposed
as a browser-global diagnostic.

Each asynchronous render owns a disposable mount; obsolete loads cannot render
into the next witness. The runtime import is shared, failed attempts are reset,
construction/load/render failures are visible and retryable, and ResizeObserver
is cleaned on unmount. Measure count, source/derived shape captions, semantic
availability, review warnings and quarantine remain separate from engraving.

A 640 CSS-pixel minimum keeps notation readable on narrow screens, inside the
existing labeled keyboard-scrollable region; page-level overflow is not needed.
The OSMD package remains a separate lazy chunk (about 378 kB gzip in this build),
not an eager addition to the reader entry. This is not the catalogue/payload
redesign in #5.

Older parser records with elision markers but missing following text nodes fail
explicitly; the adapter will not reconstruct lost source syllables. Supplying
complete `texts` plus `elision` arrays preserves their order. Engraving is not
proof of source transcription accuracy or safe repeat playback.

## Tied audio

`buildPracticeSchedule` coalesces source-encoded sound ties separately per part,
voice, staff and written pitch. A chain needs matching start/stop flags and both
scheduled and original-source adjacency. Each practice loop is independent;
repeat jumps cannot turn unrelated equal pitches into a tie. Slurs and visual-only
ties do not suppress attacks. Original witness events and repeat safety gates are
unchanged. The audio allocator makes one oscillator/envelope for each coalesced
chain and sustains it for the complete combined beat length.
