import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const books = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url))).books;
const source = {
  workTitle: 'Accessible witness', keySignature: '0:major', timeSignature: '4/4',
  transposition: { available: true },
  sourceUrl: 'https://example.invalid/accessible-witness',
  parts: [{ name: 'Tenor', clefs: { 1: 'treble' }, events: [
    { onset: 0, beats: 4, measure: '1', step: 'C', octave: 4, type: 'whole', lyrics: [{ text: 'Light & hope', number: '2' }] },
  ] }],
};

async function openScore(page) {
  const full = { ...source, scoreRef: '/accessible-witness.json' };
  await page.route('**/reader-data/catalogue.json', route => route.fulfill({ json: {
    books, songs: [{ id: 'accessibility', title: 'Accessible witness', songNo: '1', books: ['sh1991'],
      metadataByBook: { sh1991: {} }, scoreByBook: { sh1991: full } }],
  } }));
  await page.route('**/accessible-witness.json', route => route.fulfill({ json: full }));
  await page.route('**/human-review-queue.json', route => route.fulfill({ json: { reviewNow: [] } }));
  await page.route('**/source-health.json', route => route.fulfill({ json: { records: [] } }));
  await page.goto('/?book=sh1991&tune=accessibility');
  await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state', 'ready');
}

async function mountHarness(page, options = {}, harnessScore = source) {
  await openScore(page);
  await page.evaluate(async ({ score, options }) => {
    const main = await import('/src/main.jsx');
    main.atlasRoot.unmount();
    const { mountHarness } = await import('/tests/browser/engraving-harness.jsx');
    window.notationHarness = await mountHarness(document.getElementById('root'), score, options);
  }, { score: harnessScore, options });
}

test('failed notation exposes its error, then restores keyboard focus after Retry succeeds', async ({ page }) => {
  await mountHarness(page, { failOnce: true });
  await expect(page.getByRole('alert')).toContainText('Simulated runtime delivery failure');
  await expect(page.getByRole('img', { name: /Available source score/ })).toHaveCount(0);
  await expect(page.getByRole('region', { name: /Score notation/ })).toHaveCount(0);
  await expect(page.locator('.score-scroll')).toHaveAttribute('tabindex', '-1');
  await page.getByRole('button', { name: 'Retry notation' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state', 'ready');
  const notation = page.getByRole('region', { name: /Score notation/ });
  await expect(notation).toBeFocused();
  await expect(page.getByRole('img', { name: /Available source score with 1 parts; 1 measures/ })).toBeVisible();
});

for (const width of [1440, 320]) {
  test(`score text is keyboard-readable, updates with transposition, and fits at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await openScore(page);
    const alternative = page.locator('.score-text-alternative');
    await alternative.locator('summary').focus();
    await page.keyboard.press('Enter');
    await expect(alternative.getByRole('heading', { name: 'Tenor', exact: true })).toBeVisible();
    await expect(alternative.getByRole('heading', { name: 'Measure 1', exact: true })).toBeVisible();
    await expect(alternative.getByRole('listitem')).toHaveText('C octave 4; 4 quarter-note beats. Offset 0; voice 1, staff 1. Verse 2: “Light & hope”.');
    await page.getByLabel('Target key', { exact: true }).selectOption('Bb');
    await expect(alternative).toContainText('Displayed transposed pitches');
    await expect(alternative.getByRole('listitem')).toHaveText(/B flat octave 3;.*Verse 2: “Light & hope”/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator('vite-error-overlay')).toHaveCount(0);
    expect(errors).toEqual([]);
    const path = test.info().outputPath(`score-text-${width}.png`);
    await page.locator('.score-frame').screenshot({ path });
    await test.info().attach(`score-text-${width}`, { path, contentType: 'image/png' });
  });
}

test('score text stays available when the engraving runtime fails', async ({ page }) => {
  await mountHarness(page, { failOnce: true });
  await expect(page.getByRole('alert')).toContainText('Simulated runtime delivery failure');
  const alternative = page.locator('.score-text-alternative');
  await alternative.locator('summary').focus();
  await page.keyboard.press('Enter');
  await expect(alternative.getByRole('listitem')).toContainText('C octave 4; 4 quarter-note beats.');
  await expect(page.getByRole('img', { name: /Available source score/ })).toHaveCount(0);
});

test('pending engraving does not expose an empty score or keyboard scroll stop', async ({ page }) => {
  await mountHarness(page);
  await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state', 'ready');
  await page.evaluate(score => notationHarness.show({ ...score, workTitle: 'Slow witness' }), source);
  await expect.poll(() => page.evaluate(() => Boolean(notationHarness.trace.release))).toBe(true);
  await expect(page.getByRole('status')).toContainText('Engraving');
  await expect(page.getByRole('img', { name: /Available source score/ })).toHaveCount(0);
  await expect(page.locator('.score-scroll')).toHaveAttribute('tabindex', '-1');
  await page.evaluate(() => notationHarness.trace.release());
  await expect(page.getByRole('img', { name: /Available source score/ })).toBeVisible();
  await expect(page.getByRole('region', { name: /Score notation/ })).not.toBeFocused();
});

test('Retry completion preserves focus when the reader moves to another control', async ({ page }) => {
  await mountHarness(page, { failOnce: true }, { ...source, workTitle: 'Slow witness' });
  await page.getByRole('button', { name: 'Retry notation' }).focus();
  await page.keyboard.press('Enter');
  await expect.poll(() => page.evaluate(() => Boolean(notationHarness.trace.release))).toBe(true);
  await page.evaluate(() => {
    const otherControl = document.createElement('button');
    otherControl.textContent = 'Next witness';
    document.getElementById('root').after(otherControl);
    otherControl.focus();
  });
  await page.evaluate(() => notationHarness.trace.release());
  await expect(page.locator('.score-engraving')).toHaveAttribute('data-render-state', 'ready');
  await expect(page.getByRole('button', { name: 'Next witness' })).toBeFocused();
});
