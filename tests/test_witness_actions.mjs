import test from 'node:test';
import assert from 'node:assert/strict';
import { witnessFileAction } from '../src/witnessActions.js';
test('local original files download; external originals open without a download claim', () => {
  assert.deepEqual(witnessFileAction('/review/example.mxl'), {href:'/review/example.mxl',download:true,label:'Download MusicXML'});
  assert.deepEqual(witnessFileAction('https://source.test/a.musicxml'), {href:'https://source.test/a.musicxml',download:false,label:'Open external MusicXML'});
});
test('unsafe, non-score and policy-prohibited URLs have no file action', () => {
  for (const url of ['javascript:evil.xml', '//outside.test/a.xml', 'http://source.test/a.xml', 'https://u:p@source.test/a.xml', '/a.json', '/a/../b.xml', '/a/%2e%2e/b.xml', '/a\\b.xml', null]) assert.equal(witnessFileAction(url), null, String(url));
  assert.equal(witnessFileAction('/a.xml', {policy:'external-link-only'}), null);
  assert.equal(witnessFileAction('/a.xml', {policy:'private'}), null);
});
