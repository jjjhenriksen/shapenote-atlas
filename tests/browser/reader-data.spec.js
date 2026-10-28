import { unpackCatalogue } from '../../src/catalogueWire.js';
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
const publicDir = new URL('../../public/', import.meta.url);
const corpus = JSON.parse(readFileSync(new URL('corpus.json', publicDir)));
const load = (path) => JSON.parse(readFileSync(new URL(path.replace(/^\//, ''), publicDir)));
const target = corpus.songs.find((song) => song.id === 'kentucky 10 — New-Salem');
const url = `/?book=kentucky&tune=${encodeURIComponent(target.id)}`;

for (const width of [1440, 390]) {
  test(`cold catalogue/detail budget and reader interaction at ${width}px`, async ({ page, context }, testInfo) => {
    test.setTimeout(90000);
    await page.setViewportSize({width, height: width === 390 ? 844 : 1000});
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => { if (['error', 'warning'].includes(message.type()) && !/Failed to load resource|net::ERR/.test(message.text())) errors.push(message.text()); });
    const requests = [];
    page.on('request', (request) => requests.push(request.url()));
    // Isolate app transport from unrelated remote fonts/source websites.
    await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (route) => route.abort());
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', {cacheDisabled:true});
    await cdp.send('Network.emulateNetworkConditions', {offline:false, latency:150, downloadThroughput:200000, uploadThroughput:93750});
    await cdp.send('Emulation.setCPUThrottlingRate', {rate:4});
    const start = Date.now();
    await page.goto(url, {waitUntil:'domcontentloaded'});
    await expect(page.getByRole('heading', {name:'10 — New-Salem', exact:true})).toBeVisible({timeout:60000});
    const catalogueVisibleMs = Date.now() - start;
    await expect(page.getByRole('button', {name:'Play song', exact:true})).toBeEnabled({timeout:60000});
    const playableMs = Date.now() - start;
    // Production preview uses gzip. Development transforms are not the release path.
    if (process.env.ATLAS_BROWSER_PREVIEW) {
      expect(catalogueVisibleMs).toBeLessThan(6000);
      expect(playableMs).toBeLessThan(7000);
    }
    await expect(page).toHaveTitle('The Shape-Note Atlas');
    await expect(page.locator('vite-error-overlay')).toHaveCount(0);
    await page.getByTestId('tune-search').fill('New-Salem');
    await expect(page.locator('.results-list .result-row')).toHaveCount(1);
    const resources = await page.evaluate(() => performance.getEntriesByType('resource').filter((entry) => /\/reader-data\/.*\.json/.test(entry.name)).map(({name,decodedBodySize,encodedBodySize,duration}) => ({name,decodedBodySize,encodedBodySize,duration})));
    const catalogue = resources.filter((entry) => entry.name.endsWith('/catalogue.json'));
    const details = resources.filter((entry) => !entry.name.endsWith('/catalogue.json'));
    expect(catalogue).toHaveLength(1);
    expect(details).toHaveLength(1);
    expect(catalogue[0].decodedBodySize).toBeLessThanOrEqual(2300000);
    expect(catalogue[0].decodedBodySize + details[0].decodedBodySize).toBeLessThanOrEqual(3300000);
    expect(requests.filter((url) => /\/(corpus|human-review-queue|source-health)\.json/.test(url))).toEqual([]);
    expect(errors).toEqual([]);
    console.log(JSON.stringify({width, profile:'1.6 Mbps down, 150 ms latency, 4x CPU slowdown, cache disabled', catalogueVisibleMs, playableMs, resources}));
    await testInfo.attach('cold-load-measurements', {body:JSON.stringify({catalogueVisibleMs,playableMs,resources},null,2),contentType:'application/json'});
    await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state', 'ready', {timeout:30000});
    await page.screenshot({path:process.env.ATLAS_SCREENSHOTS ? join(process.env.ATLAS_SCREENSHOTS, `payload-${width}.png`) : testInfo.outputPath(`payload-${width}.png`)});
  });
}

for (const corruption of ['wrong tune', 'invalid review', 'invalid health']) test(`${corruption} detail fails closed and retries without losing selection`, async ({page}) => {
  const catalogue = unpackCatalogue(load('reader-data/catalogue.json'));
  const record = catalogue.songs.find((song) => song.id === target.id);
  const detail = load(record.detailRef);
  let attempts = 0;
  const corrupted = corruption === 'wrong tune' ? {...detail, song:corpus.songs[0]}
    : corruption === 'invalid review' ? {...detail, reviewQueue:{reviewNow:[null]}}
    : {...detail, sourceHealth:{records:[null]}};
  await page.route(`**${record.detailRef}`, (route) => route.fulfill({json: ++attempts === 1 ? corrupted : detail}));
  await page.goto(url);
  await expect(page.getByRole('alert')).toContainText('Playback remains unavailable');
  await expect(page.getByRole('button', {name:'Play song',exact:true})).toHaveCount(0);
  await page.getByRole('button', {name:'Retry tune evidence'}).click();
  await expect(page.getByRole('button', {name:'Play song',exact:true})).toBeEnabled();
  await expect(page.getByRole('heading', {name:'10 — New-Salem',exact:true})).toBeVisible();
});

test('navigation aborts obsolete tune evidence and commits only the current record', async ({page}) => {
  await page.addInitScript(() => {
    const fetch = window.fetch;
    window.__details = [];
    window.fetch = (url, options) => {
      if (/\/reader-data\/[a-f0-9]+\.json/.test(url)) {
        const item = {url,aborted:false}; __details.push(item);
        options.signal.addEventListener('abort', () => item.aborted = true);
      }
      return fetch(url,options);
    };
  });
  const catalogue = unpackCatalogue(load('reader-data/catalogue.json'));
  const record = catalogue.songs.find((song) => song.id === target.id);
  let release;
  await page.route(`**${record.detailRef}`, async (route) => {
    await new Promise((resolve) => release = resolve);
    await route.fulfill({json:load(record.detailRef)}).catch(() => {});
  });
  await page.goto(url, {waitUntil:'domcontentloaded'});
  await expect.poll(() => Boolean(release)).toBe(true);
  const next = page.locator('.result-row').filter({hasText:'Portland'}).first();
  await next.click();
  await expect.poll(() => page.evaluate(() => __details[0]?.aborted)).toBe(true);
  release();
  await expect(page.locator('.detail-header h2')).toContainText('Portland');
  await expect(page.locator('.first-line')).toContainText(corpus.songs.find((song) => song.title === 'Portland' && song.books.includes('kentucky')).rawFirstLine);
  await expect(page.getByText('Loading tune evidence…')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Play song',exact:true})).toHaveCount(0);
});

for (const root of [['s', -1], ['o', 999999], ['unknown']]) {
  test(`invalid packed catalogue ${JSON.stringify(root)} fails closed and retries`, async ({page}) => {
    const wire = load('reader-data/catalogue.json');
    let attempts = 0;
    await page.route('**/reader-data/catalogue.json', route => route.fulfill({json: ++attempts === 1 ? {...wire,root} : wire}));
    await page.goto(url);
    await expect(page.getByRole('alert')).toContainText('The local corpus bundle could not be loaded or is incompatible');
    await expect(page.getByRole('button', {name:'Play song',exact:true})).toHaveCount(0);
    await page.getByRole('button', {name:/Retry/}).click();
    await expect(page.getByRole('heading', {name:'10 — New-Salem',exact:true})).toBeVisible();
    await expect(page.getByRole('button', {name:'Play song',exact:true})).toBeEnabled();
  });
}
