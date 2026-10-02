import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const corpus = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url)));
const cases = [
  { name: 'major', ref: '/scores/e1f782a69c5812f4bcd5418a.json', field: 'scoreByBook', target: 'G', delta: -1 },
  { name: 'minor', ref: '/scores/e8a639af812f0ca7c5298b2b.json', field: 'scoreByBook', target: 'C', delta: 1 },
  { name: 'unknown key', ref: '/scores/3509deecb75016f0d85fe47d.json', field: 'scoreByBook', source: 'C:minor', target: 'D', delta: 2 },
  { name: 'reference', ref: '/scores/e1f782a69c5812f4bcd5418a.json', field: 'referenceScoreByBook', target: 'G', delta: -1 },
  { name: 'draft', ref: '/draft-scores/d70b33f990339c1c2aab49d0.json', field: 'draftScoreByBook', target: 'C', delta: 5 },
];
for (const item of cases) {
  test(`bundled ${item.name} witness plays and transposes through real Web Audio`, async ({ page }) => {
    const song = corpus.songs.find((song) => Object.values(song[item.field] || {}).some((score) => score.scoreRef === item.ref));
    expect(song).toBeTruthy();
    const book = Object.keys(song[item.field]).find((book) => song[item.field][book].scoreRef === item.ref);
    const errors = []; page.on('pageerror', (error) => errors.push(error.message));
    await page.addInitScript(() => {
      const Native = window.AudioContext;
      window.__frequencies = [];
      window.AudioContext = class extends Native {
        createOscillator() {
          const node = super.createOscillator(); const start = node.start.bind(node);
          node.start = (at) => { __frequencies.push(node.frequency.value); start(at); };
          return node;
        }
      };
    });
    await page.goto(`/?book=${book}&tune=${encodeURIComponent(song.id)}`);
    await expect(page.getByRole('heading', { name: `${song.songNo} — ${song.title}`, exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
    if (item.source) await page.getByLabel('Source key', { exact: true }).selectOption(item.source);
    if (item.name === 'reference') await expect(page.locator('.reference-score-note')).toBeVisible();
    if (item.name === 'draft') await expect(page.locator('.draft-score-note')).toBeVisible();
    await page.getByRole('button', { name: 'Play song', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
    await expect.poll(() => page.evaluate(() => __frequencies.length)).toBeGreaterThan(0);
    const source = await page.evaluate(() => __frequencies[0]);
    expect(source).toBeGreaterThan(0);
    await page.getByRole('button', { name: 'Stop', exact: true }).click();
    await page.getByLabel('Target key', { exact: true }).selectOption(item.target);
    await page.evaluate(() => __frequencies.length = 0);
    await page.getByRole('button', { name: 'Play song', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
    await expect.poll(() => page.evaluate(() => __frequencies.length)).toBeGreaterThan(0);
    const target = await page.evaluate(() => __frequencies[0]);
    expect(target / source).toBeCloseTo(2 ** (item.delta / 12), 5);
    await page.getByRole('button', { name: 'Stop', exact: true }).click();
    expect(errors).toEqual([]);
  });
}

test('desktop and mobile preserve tune search, selection and encoded-repeat practice controls', async ({ page }) => {
  const errors = []; page.on('pageerror', (error) => errors.push(error.message));
  const warnings = []; page.on('console', (message) => { if (['error', 'warning'].includes(message.type())) warnings.push(message.text()); });
  await page.goto('/?book=kentucky&tune=kentucky%2010%20%E2%80%94%20New-Salem');
  await expect(page).toHaveTitle('The Shape-Note Atlas');
  await expect(page.getByRole('heading', { name: 'Shape-Note Atlas', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '10 — New-Salem', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Practice', exact: true }).click();
  await page.getByLabel('Playback order', { exact: true }).selectOption('repeats');
  await page.getByLabel('Playback loops', { exact: true }).selectOption('2');
  await expect(page.getByLabel('Playback order', { exact: true })).toHaveValue('repeats');
  await expect(page.locator('vite-error-overlay')).toHaveCount(0);
  if (process.env.ATLAS_SCREENSHOTS) await page.screenshot({ path: join(process.env.ATLAS_SCREENSHOTS, 'reader-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: '10 — New-Salem', exact: true })).toBeVisible();
  await expect(page.getByLabel('Playback loops', { exact: true })).toHaveValue('2');
  await expect(page.getByLabel('Playback order', { exact: true })).toHaveValue('repeats');
  if (process.env.ATLAS_SCREENSHOTS) await page.screenshot({ path: join(process.env.ATLAS_SCREENSHOTS, 'reader-mobile.png') });
  await page.getByLabel('Playback order', { exact: true }).scrollIntoViewIfNeeded();
  if (process.env.ATLAS_SCREENSHOTS) await page.screenshot({ path: join(process.env.ATLAS_SCREENSHOTS, 'reader-mobile-practice.png') });
  await page.getByTestId('tune-search').fill('New-Salem');
  await expect(page.locator('.results-list .result-row')).toHaveCount(1);
  expect(errors).toEqual([]);
  // External font/source availability is independent; application console
  // failures still fail this smoke test.
  expect(warnings.filter((message) => !/Failed to load resource|net::ERR/.test(message))).toEqual([]);
});
