import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {scoreToMusicXml} from '../src/scoreMusicXml.js';
import {sourceTieXml} from '../src/scoreTies.js';
test('Salem same-measure and cross-measure ties retain visual and sound identities',()=>{
 const source=JSON.parse(readFileSync(new URL('../public/scores/a44b1cd022a09f20bdb403a3.json',import.meta.url)));const {xml}=scoreToMusicXml(source);
 assert.equal((xml.match(/<tie type="start"/g)||[]).length,6);assert.equal((xml.match(/<tied type="start"/g)||[]).length,6);
 assert.match(xml,/<tied type="start" number="1" orientation="over" placement="above"\/>/);
 assert.match(xml,/<measure number="10"[\s\S]*?<tied type="stop"/);
});
test('slurs, rest and untied repetitions never become ties',()=>{
 assert.deepEqual(sourceTieXml({rest:true,tieStart:true}),{sound:'',notations:''});assert.deepEqual(sourceTieXml({}),{sound:'',notations:''});
 assert.deepEqual(sourceTieXml({editorialMarkings:[{kind:'slur',type:'start',number:'2'}]}),{sound:'',notations:'<slur type="start" number="2"/>'});
});
test('middle chain segments retain stop then start and visual-only ties stay visual',()=>{
 assert.equal(sourceTieXml({tieStart:true,tieStop:true}).sound,'<tie type="stop"/><tie type="start"/>');
 const visual=sourceTieXml({editorialMarkings:[{kind:'tied',type:'start',number:'1'}]});assert.equal(visual.sound,'');assert.match(visual.notations,/<tied/);
});
