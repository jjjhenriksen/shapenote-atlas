import { test } from 'node:test';
import assert from 'node:assert/strict';
import { packCatalogue, unpackCatalogue } from '../src/catalogueWire.js';
test('transport is lossless including null, arrays, special keys, and repeated values', () => {
  const value = JSON.parse('{"__proto__":{"polluted":true},"array":[null,false,0,"s",["o",1]],"one":"long repeated provenance source string","two":"long repeated provenance source string"}');
  assert.deepEqual(unpackCatalogue(packCatalogue(value)), value);
  assert.equal({}.polluted, undefined);
});
test('legacy payloads are passed to existing corpus validation unchanged', () => {
  const value = {readerDataVersion:1,songs:[]};
  assert.equal(unpackCatalogue(value), value);
});
test('invalid wire versions, tags, references, shapes and arity fail closed', () => {
  const base = {catalogueWireVersion:1,shapes:[['id']],strings:['value'],root:['o',0,'value']};
  for (const change of [
    {catalogueWireVersion:2}, {strings:[null]}, {shapes:[['id','id']]},
    {root:['s',-1]}, {root:['s',0,1]}, {root:['o',99]}, {root:['o',0]},
    {root:['o',0,'value','extra']}, {root:['unknown']}, {root:{id:'value'}},
  ]) assert.throws(() => unpackCatalogue({...base,...change}), /Incompatible/);
  let root = null;
  for (let i=0;i<66;i++) root=['a',root];
  assert.throws(() => unpackCatalogue({...base,root}), /Incompatible/);
});
