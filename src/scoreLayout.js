// Reserve a staff row plus space for each source-encoded verse.
export function scoreSystemLayout(parts) {
  const verseRows = Math.max(0, ...parts.map(part => new Set((part.lyrics || []).map(lyric => String(lyric.number || '1'))).size));
  const staffGap = 47 + verseRows * 12;
  return { staffGap, systemHeight: 26 + Math.max(1, parts.length) * staffGap };
}
