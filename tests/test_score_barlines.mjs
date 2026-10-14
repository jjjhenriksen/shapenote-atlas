import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {scoreToMusicXml} from '../src/scoreMusicXml.js';
import {measureBarlines} from '../src/scoreBarlines.js';
const load=(name)=>JSON.parse(readFileSync(new URL(`../public/draft-scores/${name}.json`,import.meta.url)));
test('New Salem terminal backward repeat remains at right of measure 16',()=>{
 const {xml}=scoreToMusicXml(load('kentucky-new-salem-v3'));
 assert.match(xml,/<measure number="16"[\s\S]*?<barline location="right"><bar-style>light-heavy<\/bar-style><repeat direction="backward"\/><\/barline><\/measure>/);
 assert.doesNotMatch(xml,/<repeat direction="forward"/);
});
test('Devotion first/second endings and source forward/backward repeat are engraved independently of playback safety',()=>{
 const source=load('sh2025-50t-devotion-v10');source.playback={status:'blocked',safeToApply:false};
 const {xml}=scoreToMusicXml(source);
 for(const number of ['1','2'])for(const type of ['start','stop'])assert.ok(xml.includes(`<ending number="${number}" type="${type}"/>`));
 assert.match(xml,/<repeat direction="forward"/);assert.match(xml,/<repeat direction="backward"/);
});
test('canonical measure records override legacy lines; no repeats invented for Something New',()=>{
 assert.deepEqual(measureBarlines({measureSemantics:[{number:'1',barlines:[]}],barlines:[{measure:'1',repeat:{direction:'backward'}}]},'1'),[]);
 assert.doesNotMatch(scoreToMusicXml(load('shenandoah-something-new-v3')).xml,/<repeat|<ending/);
});
