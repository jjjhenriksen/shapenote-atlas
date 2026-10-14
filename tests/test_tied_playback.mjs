import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildPracticeSchedule} from '../src/practice.js';
import {coalesceSourceTies} from '../src/tiedPlayback.js';
const note=(onset,extra={})=>({onset,beats:1,measure:String(onset+1),step:'C',octave:5,voice:'1',staff:'1',...extra});
test('real Salem C5 sustains five beats with no event/attack at beat 27',()=>{
 const source=JSON.parse(readFileSync(new URL('../public/scores/a44b1cd022a09f20bdb403a3.json',import.meta.url)));const before=JSON.stringify(source);
 const result=buildPracticeSchedule(source.parts,null);
 const treble=result.events.filter(e=>e.partName==='Treble');assert.equal(treble.find(e=>e.scheduledOnset===24).beats,5);assert.equal(treble.find(e=>e.scheduledOnset===24).tiedSegments,2);assert.ok(!treble.some(e=>e.scheduledOnset===27));
 assert.equal(treble.find(e=>e.scheduledOnset===48).beats,5);assert.equal(JSON.stringify(source),before);
});
test('middle chain segments sustain, but untied repeated notes and slurs reattack',()=>{
 const result=coalesceSourceTies([note(0,{tieStart:true}),note(1,{tieStop:true,tieStart:true}),note(2,{tieStop:true}),note(3),note(4,{editorialMarkings:[{kind:'slur',type:'start'}]})]);
 assert.deepEqual(result.map(e=>[e.onset,e.beats]),[[0,3],[3,1],[4,1]]);
});
test('staff, voice, pitch, part and gaps prevent accidental tie merging',()=>{
 for(const change of [{staff:'2'},{voice:'2'},{step:'D'},{onset:2},{tieStop:false}])assert.equal(coalesceSourceTies([note(0,{tieStart:true}),note(1,{tieStop:true,...change})]).length,2);
 const sameName=[{name:'Shared',events:[note(0,{tieStart:true})]},{name:'Shared',events:[note(1,{tieStop:true})]}];assert.equal(buildPracticeSchedule(sameName,null).events.length,2);
});
test('repeat visits coalesce internal chains but repeat jumps and practice-loop boundaries stay separate',()=>{
 const parts=[{name:'A',events:[note(0,{tieStart:true}),note(1,{tieStop:true})]}];
 const plan={status:'encoded',safeToApply:true,measureSequence:['1','2','1','2'],measureStarts:{1:0,2:1},measureDurations:{1:1,2:1}};
 const result=buildPracticeSchedule(parts,plan,2);assert.equal(result.duration,8);assert.deepEqual(result.events.map(e=>[e.scheduledOnset,e.beats]),[[0,2],[2,2],[4,2],[6,2]]);
 const jump=buildPracticeSchedule([{name:'A',events:[note(0,{tieStop:true}),note(1,{tieStart:true})]}],plan,2);assert.equal(jump.events.length,8);
});
test('mismatched enharmonic spelling is not an inferred source tie',()=>{
 assert.equal(coalesceSourceTies([note(0,{step:'B',alter:-1,octave:4,tieStart:true}),note(1,{step:'A',alter:1,octave:4,tieStop:true})]).length,2);
});
