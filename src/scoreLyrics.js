import { xmlText, tag } from './musicXmlText.js';

export function lyricXml(lyric) {
  const texts = lyric.texts || [lyric.text || ''];
  // Older parser output can retain elisions without the following text nodes.
  // Do not silently manufacture or drop the missing syllable.
  if ((lyric.elision?.length || 0) >= texts.length) throw new Error('Source lyric elision text is incomplete; inspect the source MusicXML.');
  const syllabic = ['single', 'begin', 'middle', 'end'].includes(lyric.syllabic) ? tag('syllabic', lyric.syllabic) : '';
  const text = texts.map((value, index) => `${index ? tag('elision', lyric.elision?.[index - 1] || ' ') : ''}${tag('text', value)}`).join('');
  const extend = lyric.extend === true || (lyric.extend && typeof lyric.extend === 'object')
    ? `<extend${['start', 'continue', 'stop'].includes(lyric.extend?.type) ? ` type="${lyric.extend.type}"` : ''}/>` : '';
  return `<lyric number="${xmlText(lyric.number || lyric.verse || '1')}"${lyric.name ? ` name="${xmlText(lyric.name)}"` : ''}>${syllabic}${text}${extend}${lyric.endLine ? '<end-line/>' : ''}${lyric.endParagraph ? '<end-paragraph/>' : ''}</lyric>`;
}
