import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sourceNoteheadEvidence, noteheadFilled } from '../src/noteheadEvidence.js';

test('Glimpse literal glyphs render without inventing a source key or sol assignment', () => {
  const score=JSON.parse(readFileSync(new URL('../public/draft-scores/sacredharptunes-glimpse-v1.json',import.meta.url)));
  assert.equal(score.keyEvidence.status,'unknown');
  const events=score.parts.flatMap(p=>p.events).filter(e=>!e.rest);
  const counts={};
  for(const event of events) {
    const evidence=sourceNoteheadEvidence(event);
    assert.equal(evidence.kind,'source');
    counts[evidence.name]=(counts[evidence.name]||0)+1;
  }
  assert.deepEqual(counts,{round:18,fa:22,la:16,mi:4});
  assert.equal(score.transposition.available,false);
});

test('unsupported explicit and seven-shape glyphs stay unavailable, not key-derived four-shapes', () => {
  for(const notehead of ['do','re','ti','cross','x','__proto__','constructor']) {
    assert.deepEqual(sourceNoteheadEvidence({notehead,shape:'fa'}),{name:'',kind:'unavailable'});
  }
  assert.equal(sourceNoteheadEvidence({step:'C'}),null);
  assert.deepEqual(sourceNoteheadEvidence({shape:'sol'}),{name:'sol',kind:'source'});
  assert.deepEqual(sourceNoteheadEvidence({notehead:'normal',shape:'sol'}),{name:'round',kind:'source'});
});

test('explicit open/filled state wins over duration while omitted state keeps duration rendering', () => {
  assert.equal(noteheadFilled({type:'quarter',noteheadFilled:false}),false);
  assert.equal(noteheadFilled({type:'half',noteheadFilled:true}),true);
  assert.equal(noteheadFilled({type:'half'}),false);
  assert.equal(noteheadFilled({type:'eighth'}),true);
});
