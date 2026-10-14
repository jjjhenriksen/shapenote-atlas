import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { scoreToMusicXml } from '../src/scoreMusicXml.js';
import { lyricXml } from '../src/scoreLyrics.js';
const note = (overrides={}) => ({ onset: 0, beats: 1, measure: '1', step: 'C', octave: 4, ...overrides });
test('Devotion carries encoded Sweet syllables and New Salem does not invent underlay', () => {
 const devotion = JSON.parse(readFileSync(new URL('../public/draft-scores/sh2025-50t-devotion-v10.json',import.meta.url)));
 const { xml }=scoreToMusicXml(devotion); assert.match(xml, /<text>Sweet<\/text>/);assert.match(xml, /<syllabic>begin<\/syllabic><text>sa<\/text>/);
 const plain=JSON.parse(readFileSync(new URL('../public/draft-scores/kentucky-new-salem-v3.json',import.meta.url)));assert.doesNotMatch(scoreToMusicXml(plain).xml, /<lyric/);
});
test('verses, syllabification, complete elisions and extensions are encoded safely', () => {
 assert.equal(lyricXml({number:'2',syllabic:'middle',texts:['love','and'],elision:[' '],extend:{type:'start'}}),'<lyric number="2"><syllabic>middle</syllabic><text>love</text><elision> </elision><text>and</text><extend type="start"/></lyric>');
 assert.match(lyricXml({text:'<source>&',extend:true}),/<text>&lt;source&gt;&amp;<\/text><extend\/>/);
 assert.throws(()=>lyricXml({text:'one',elision:[' ']}),/incomplete/);
});
test('score-level lyric event indexes remain bound to their original part after suppression', () => {
 const score={parts:[{name:'A',events:[note(),note({step:'E'}),note({onset:1})]},{name:'B',events:[note()]}],lyrics:[{partId:'P1',eventIndex:2,number:'1',text:'kept'},{partId:'P2',eventIndex:0,number:'2',text:'other'}]};
 const {xml}=scoreToMusicXml(score,{reviewDraft:true});assert.equal((xml.match(/<text>kept<\/text>/g)||[]).length,1);assert.equal((xml.match(/<text>other<\/text>/g)||[]).length,1);assert.match(xml,/<lyric number="2">/);
});
