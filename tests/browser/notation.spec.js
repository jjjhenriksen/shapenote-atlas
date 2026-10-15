import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
const load = (path) => JSON.parse(readFileSync(new URL(`../../public/${path}`, import.meta.url)));
const books = load('corpus.json').books;
async function openScore(page, score) {
 const full = { ...score, scoreRef: '/notation-source.json' };
 await page.route('**/reader-data/catalogue.json', route => route.fulfill({json:{ books, songs:[{id:'notation',title:'Notation fixture',songNo:'1',books:['sh1991'],metadataByBook:{sh1991:{}},scoreByBook:{sh1991:full}}]}}));
 await page.route('**/notation-source.json',route=>route.fulfill({json:full}));
 await page.route('**/human-review-queue.json',route=>route.fulfill({json:{reviewNow:[]}}));
 await page.route('**/source-health.json',route=>route.fulfill({json:{records:[]}}));
 await page.goto('/?book=sh1991&tune=notation');
 await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state','ready');
}
async function attachScore(page, name) {
 const path = test.info().outputPath(`${name}.png`);
 await page.locator('.score-frame').screenshot({path});
 await test.info().attach(name, {path, contentType:'image/png'});
}
const lyricOverlap = (page) => page.locator('.score-engraving').evaluate(element => {
 const labels=[...element.querySelectorAll('.lyrics')].map(node=>({text:node.textContent,box:node.getBoundingClientRect()}));
 return labels.flatMap((a,i)=>labels.slice(i+1).filter(b=>Math.abs(a.box.y-b.box.y)<2 && Math.min(a.box.right,b.box.right)-Math.max(a.box.x,b.box.x)>0.5).map(b=>[a.text,b.text]));
});
for (const width of [1440,390,320]) {
 test(`Devotion source shapes, lyrics and endings render without collisions at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await openScore(page,load('draft-scores/sh2025-50t-devotion-v10.json'));
  await expect(page.locator('.score-engraving')).toContainText('Sweet');
  await expect(page.locator('.score-engraving .lyrics')).not.toHaveCount(0);
  await expect(page.locator('.score-engraving')).toContainText('1');await expect(page.locator('.score-engraving')).toContainText('2');
  expect(await lyricOverlap(page)).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('region',{name:/Score notation/}).focus();await expect(page.getByRole('region',{name:/Score notation/})).toBeFocused();
  expect(errors).toEqual([]);await expect(page.locator('vite-error-overlay')).toHaveCount(0);
  await attachScore(page, `devotion-${width}`);
  if(process.env.ATLAS_SCREENSHOTS)await page.locator('.score-frame').screenshot({path:join(process.env.ATLAS_SCREENSHOTS,`devotion-notation-${width}.png`)});
 });
}
test('New Salem repeat engraving preserves the no-lyrics availability warning',async({page})=>{
 await openScore(page,load('draft-scores/kentucky-new-salem-v3.json'));
 await expect(page.locator('.semantic-summary')).toContainText('Repeats: Source-encoded');
 await expect(page.locator('.semantic-summary')).toContainText('Lyrics: Unavailable');
 await expect(page.locator('.score-engraving .lyrics')).toHaveCount(0);
 await attachScore(page, 'new-salem');
 if(process.env.ATLAS_SCREENSHOTS)await page.locator('.score-frame').screenshot({path:join(process.env.ATLAS_SCREENSHOTS,'new-salem-notation.png')});
});
test('Salem ties include cross-system arcs and untied control has fewer rendered curves',async({page})=>{
 const source=load('scores/a44b1cd022a09f20bdb403a3.json');await openScore(page,source);
 const curves=()=>page.locator('.score-engraving svg path').evaluateAll(nodes=>nodes.filter(node=>/C|Q/.test(node.getAttribute('d')||'')).length);
 const before=await curves();
 await attachScore(page, 'salem-ties');
 if(process.env.ATLAS_SCREENSHOTS)await page.locator('.score-frame').screenshot({path:join(process.env.ATLAS_SCREENSHOTS,'salem-ties.png')});
 const control=structuredClone(source);for(const part of control.parts)for(const event of part.events){delete event.tieStart;delete event.tieStop;event.editorialMarkings=(event.editorialMarkings||[]).filter(mark=>mark.kind!=='tied');}
 await page.evaluate(async(score)=>{const main=await import('/src/main.jsx');main.atlasRoot.unmount();const {mountHarness}=await import('/tests/browser/engraving-harness.jsx');window.notationHarness=await mountHarness(document.getElementById('root'),score);},control);
 await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state','ready');expect(await curves()).toBeLessThan(before);
});
test('runtime failure retries successfully; obsolete witness cannot overwrite the current engraving',async({page})=>{
 const source=load('scores/a44b1cd022a09f20bdb403a3.json');await openScore(page,source);
 await page.evaluate(async(score)=>{const main=await import('/src/main.jsx');main.atlasRoot.unmount();const {mountHarness}=await import('/tests/browser/engraving-harness.jsx');window.notationHarness=await mountHarness(document.getElementById('root'),score,{failOnce:true});},source);
 await expect(page.getByRole('alert')).toContainText('Simulated runtime delivery failure');
 await page.getByRole('button',{name:'Retry notation'}).click();await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state','ready');
 await page.evaluate((score)=>notationHarness.show({...score,workTitle:'Slow witness'}),source);
 await expect.poll(()=>page.evaluate(()=>Boolean(notationHarness.trace.release))).toBe(true);
 await page.evaluate((score)=>notationHarness.show({...score,workTitle:'Current witness'}),source);
 await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state','ready');
 await page.evaluate(()=>notationHarness.trace.release());
 expect(await page.evaluate(()=>notationHarness.trace.renders)).not.toContain('Slow witness');
 await expect(page.locator('.notation-mount')).toHaveCount(1);
 await page.evaluate(()=>notationHarness.unmount());await expect(page.locator('.notation-mount')).toHaveCount(0);
});

test('real Web Audio gives a five-beat tied chain one attack and full sustain',async({page})=>{
 const source={sourceUrl:'https://example.invalid/tie-fixture',keySignature:'0:major',timeSignature:'4/4',transposition:{available:true},parts:[{name:'Tenor',clefs:{1:'treble'},events:[{onset:0,beats:3,measure:'1',step:'C',octave:5,type:'half',dots:1,tieStart:true},{onset:3,beats:2,measure:'2',step:'C',octave:5,type:'half',tieStop:true}]}]};
 await page.addInitScript(()=>{
  const Native=window.AudioContext;window.tieAttacks=[];
  window.AudioContext=class extends Native{createOscillator(){const node=super.createOscillator();const record={};tieAttacks.push(record);const start=node.start.bind(node),stop=node.stop.bind(node);node.start=at=>{record.start=at;start(at);};node.stop=at=>{record.stop=at;stop(at);};return node;}};
 });
 await openScore(page,source);await page.getByLabel('Tempo BPM',{exact:true}).fill('220');
 await page.getByRole('button',{name:'Play song',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>tieAttacks.length)).toBe(1);
 const attack=await page.evaluate(()=>({...tieAttacks[0]}));expect(attack.stop-attack.start).toBeCloseTo(5*60/220+0.15,5);
 await page.waitForTimeout(1000);expect(await page.evaluate(()=>tieAttacks.length)).toBe(1);
 await page.getByRole('button',{name:'Stop',exact:true}).click();
});
