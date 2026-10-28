// File actions preserve source bytes; never export the transposed rendering.
export function witnessFileAction(url, { label = 'MusicXML', policy } = {}) {
  if (typeof url !== 'string' || !url || /[\s\\]/.test(url) || /%(?:2e|2f|5c)/i.test(url)) return null;
  const local = url.startsWith('/') && !url.startsWith('//');
  if (!local && !url.startsWith('https://')) return null;
  let parsed;
  try { parsed = new URL(url, 'https://atlas.invalid'); } catch { return null; }
  if ((!local && parsed.protocol !== 'https:') || parsed.username || parsed.password) return null;
  if (!/\.(?:musicxml|xml|mxl)$/i.test(parsed.pathname) || url.split('/').includes('..')) return null;
  if (policy && !['copy', 'external-link-only'].includes(policy)) return null;
  if (policy === 'external-link-only' && local) return null;
  return { href: url, download: local, label: `${local ? 'Download' : 'Open external'} ${label}` };
}
