# Agent-11 semantic fixture

`semantic-fixture.xml` is a synthetic, bounded parser fixture for the
lyrics/repeats backlog. Its lyric words and repeat/ending attributes are
manually assembled from separate review evidence: the first printed lyric line
of the retained Passing Away source scan (`work/omr/445-passing-away/source.jpg`)
and repeat/ending attributes observed in the retained structured witness
(`work/445.mxl`). The XML itself is not a retained source witness, does not
establish source lyric alignment, and is never a promotable 2025
transcription.

The production parser must keep those evidence classes separate: source
MusicXML controls encoded event semantics, scans can establish visible text or
marks, and absent event-level data remains unavailable.
