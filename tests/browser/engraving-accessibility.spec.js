import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const books = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url))).books;
const source = {
  workTitle: 'Accessible witness', keySignature: '0:major', timeSignature: '4/4',
  sourceUrl: 'https://example.invalid/accessible-witness',
  parts: [{ name: 'Tenor', clefs: { 1: 'treble' }, events: [
    { onset: 0, beats: 4, measure: '1', step: 'C', octave: 4, type: 'whole' },
  ] }],
};

async function mountHarness(page, options = {}, harnessScore = source) {
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
