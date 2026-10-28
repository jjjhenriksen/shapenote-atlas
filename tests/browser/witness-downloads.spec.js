import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createServer, get } from 'node:http';
let server, origin, failNext;
test.beforeEach(async () => {
  failNext = false;
  server = createServer((req, res) => {
    if (req.url === '/fixture-original.musicxml') {
      if (failNext) { failNext = false; res.writeHead(503).end('Unavailable'); return; }
      res.writeHead(200, {'Content-Type':'application/vnd.recordare.musicxml+xml'}).end(xml); return;
    }
    const upstream = get('http://127.0.0.1:5173' + req.url, response => { res.writeHead(response.statusCode, response.headers); response.pipe(res); });
    upstream.on('error', () => res.writeHead(502).end());
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
});
test.afterEach(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); });
const corpus = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url)));
const xml = Buffer.from('<?xml version="1.0"?><score-partwise version="4.0"><work><work-title>Original witness</work-title></work></score-partwise>');
async function fixture(page, sourceUrl) {
  const score = {sourceUrl,scoreRef:'/fixture-score.json',keySignature:'0:major',transposition:{available:true},parts:[{name:'Tenor',events:[{step:'C',octave:4,onset:0,beats:1,measure:1,type:'quarter'}]}]};
  await page.route('**/reader-data/catalogue.json', route => route.fulfill({json:{books:{sh1991:corpus.books.sh1991},songs:[{id:'witness',title:'Witness',songNo:'1',books:['sh1991'],metadataByBook:{sh1991:{}},scoreByBook:{sh1991:score}}]}}));
  await page.route('**/fixture-score.json', route => route.fulfill({json:score}));
  await page.route('**/source-health.json', route => route.fulfill({json:{records:[]}}));
  await page.route('**/human-review-queue.json', route => route.fulfill({json:{reviewNow:[]}}));
  await page.goto(origin + '/?book=sh1991&tune=witness');
  await expect(page.getByRole('button',{name:'Play song',exact:true})).toBeEnabled();
}
for (const width of [1440, 390]) test(`original XML download preserves bytes and keyboard access at ${width}px`, async ({page}, info) => {
  await page.setViewportSize({width,height:900});
  await fixture(page, '/fixture-original.musicxml');
  const link = page.getByRole('link',{name:'Download source MusicXML (original file)'});
  await link.focus(); await expect(link).toBeFocused();
  await page.getByRole('button', {name:'Transpose down one semitone',exact:true}).click();
  await link.focus();
  const result = page.waitForEvent('download'); await link.press('Enter');
  const download = await result;
  expect(await download.failure()).toBeNull();
  expect(readFileSync(await download.path())).toEqual(xml);
  await expect(link).toHaveAttribute('title', /Original file; display transposition is not applied/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`witness-${width}.png`),fullPage:true});
});
test('external source is an explicit external link, never a local download claim', async ({page}) => {
  await fixture(page, 'https://example.invalid/original.mxl');
  const link = page.getByRole('link',{name:'Open external source MusicXML (original file)'});
  await expect(link).toHaveAttribute('href','https://example.invalid/original.mxl');
  await expect(link).not.toHaveAttribute('download');
  await expect(link).toHaveAttribute('target','_blank');
});
test('failed original-file download can be retried without changing selection', async ({page}) => {
  failNext = true;
  await fixture(page, '/fixture-original.musicxml');
  const link = page.getByRole('link',{name:'Download source MusicXML (original file)'});
  const failed = page.waitForEvent('download'); await link.click();
  expect(await (await failed).failure()).not.toBeNull();
  await expect(page.getByRole('heading',{name:'1 — Witness',exact:true})).toBeVisible();
  const retry = page.waitForEvent('download'); await link.click();
  expect(readFileSync(await (await retry).path())).toEqual(xml);
});

test('retained MXL download preserves actual archive bytes', async ({page}) => {
  const path = '/review-publications/sh2025-557-new-farewell-v2-musicXml.mxl';
  await fixture(page, path);
  const result = page.waitForEvent('download');
  await page.getByRole('link',{name:'Download source MusicXML (original file)'}).click();
  expect(readFileSync(await (await result).path())).toEqual(readFileSync(new URL('../../public' + path, import.meta.url)));
});
