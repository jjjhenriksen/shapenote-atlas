import { xmlText, tag } from './musicXmlText.js';

export function measureBarlines(part, number) {
  const encoded = part.measureSemantics?.find((measure) => String(measure.number) === String(number));
  return encoded ? encoded.barlines || [] : (part.barlines || []).filter((line) => String(line.measure) === String(number));
}

export function barlineXml(line) {
  const location = ['left', 'right', 'middle'].includes(line.location) ? line.location : 'right';
  const styles = new Set(['regular', 'dotted', 'dashed', 'heavy', 'light-light', 'light-heavy', 'heavy-light', 'heavy-heavy', 'tick', 'short', 'none']);
  const style = styles.has(line.style) ? tag('bar-style', line.style) : '';
  const ending = line.ending && ['start', 'stop', 'discontinue'].includes(line.ending.type)
    ? `<ending number="${xmlText(line.ending.number)}" type="${line.ending.type}"/>` : '';
  const repeat = ['forward', 'backward'].includes(line.repeat?.direction)
    ? `<repeat direction="${line.repeat.direction}"${line.repeat.times ? ` times="${xmlText(line.repeat.times)}"` : ''}/>` : '';
  return `<barline location="${location}">${style}${ending}${repeat}</barline>`;
}
