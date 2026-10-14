import { xmlText } from './musicXmlText.js';

// Sound ties and visual ties/slurs are distinct MusicXML contracts. A slur
// never becomes a sound tie; engraving never changes playback planning.
export function sourceTieXml(event) {
  if (event.rest) return { sound: '', notations: '' };
  const types = ['stop', 'start'].filter((type) => event[`tie${type[0].toUpperCase()}${type.slice(1)}`]);
  const encoded = (event.editorialMarkings || []).filter((mark) => mark.kind === 'tied' && ['start', 'stop', 'continue'].includes(mark.type));
  const visual = encoded.length ? encoded : types.map((type) => ({ type }));
  const ties = visual.map((mark) => `<tied type="${mark.type}"${mark.number ? ` number="${xmlText(mark.number)}"` : ''}${['over','under'].includes(mark.orientation) ? ` orientation="${mark.orientation}"` : ''}${['above','below'].includes(mark.placement) ? ` placement="${mark.placement}"` : ''}/>`).join('');
  const slurs = (event.editorialMarkings || []).filter((mark) => mark.kind === 'slur' && ['start', 'stop', 'continue'].includes(mark.type));
  return { sound: types.map((type) => `<tie type="${type}"/>`).join(''), notations: ties + slurs.map((mark) => `<slur type="${mark.type}" number="${xmlText(mark.number || '1')}"/>`).join('') };
}
