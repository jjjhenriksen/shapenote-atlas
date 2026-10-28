// Versioned lossless transport: shared object shapes and repeated long strings.
// Decoding restores the v1 catalogue before any existing validation/reader logic.
export function packCatalogue(catalogue) {
  const counts = new Map();
  function count(value) {
    if (typeof value === 'string' && value.length >= 24) counts.set(value, (counts.get(value) || 0) + 1);
    else if (value && typeof value === 'object') Object.values(value).forEach(count);
  }
  count(catalogue);
  const strings = [...counts].filter(([, n]) => n > 1).map(([s]) => s);
  const stringIds = new Map(strings.map((s, i) => [s, i]));
  const shapes = [], shapeIds = new Map();
  function encode(value) {
    if (typeof value === 'string' && stringIds.has(value)) return ['s', stringIds.get(value)];
    if (Array.isArray(value)) return ['a', ...value.map(encode)];
    if (value && typeof value === 'object') {
      const keys = Object.keys(value), key = JSON.stringify(keys);
      if (!shapeIds.has(key)) { shapeIds.set(key, shapes.length); shapes.push(keys); }
      return ['o', shapeIds.get(key), ...keys.map(k => encode(value[k]))];
    }
    return value;
  }
  const root = encode(catalogue);
  return { catalogueWireVersion: 1, shapes, strings, root };
}

export function unpackCatalogue(wire) {
  // Legacy catalogue fixtures and cached v1 builds remain readable.
  if (!wire || !Object.hasOwn(wire, 'catalogueWireVersion')) return wire;
  const fail = () => { throw new Error('Incompatible packed reader catalogue'); };
  if (wire.catalogueWireVersion !== 1 || !Array.isArray(wire.shapes) || !Array.isArray(wire.strings)
    || wire.strings.some(s => typeof s !== 'string')
    || wire.shapes.some(keys => !Array.isArray(keys) || keys.some(k => typeof k !== 'string') || new Set(keys).size !== keys.length)) fail();
  const index = (n, table) => Number.isInteger(n) && n >= 0 && n < table.length;
  function decode(value, depth = 0) {
    if (depth > 64) return fail();
    if (!Array.isArray(value)) {
      if (value !== null && typeof value === 'object') return fail();
      return value;
    }
    const [tag, id] = value;
    if (tag === 's' && value.length === 2 && index(id, wire.strings)) return wire.strings[id];
    if (tag === 'a') return value.slice(1).map(v => decode(v, depth + 1));
    if (tag === 'o' && index(id, wire.shapes)) {
      const keys = wire.shapes[id];
      if (value.length !== keys.length + 2) return fail();
      // fromEntries treats __proto__ as data, never a prototype mutation.
      return Object.fromEntries(keys.map((key, i) => [key, decode(value[i + 2], depth + 1)]));
    }
    return fail();
  }
  return decode(wire.root);
}
