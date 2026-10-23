import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const corpus = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url)));
const socialHarp = corpus.songs.filter(song => song.books.includes('socialharp'));

for (const width of [1440, 390]) {
  for (const [facet, value, fallback] of [
    ['Key filter', 'C', 'all'],
    ['Available part filter', 'Treble', 'all'],
  ]) {
    test(`changing books clears an unavailable ${facet} at ${width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      // Remote source sites/fonts are outside this local interaction check.
      await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
      await page.goto('/?book=sh1991');
      await expect(page).toHaveTitle('The Shape-Note Atlas');
      await page.getByLabel(facet, { exact: true }).selectOption(value);
      await expect(page.locator('.result-row').first()).toBeVisible();
      await page.getByLabel('Tune book', { exact: true }).selectOption('socialharp');
      await expect(page.getByLabel(facet, { exact: true })).toHaveValue(fallback);
      await expect(page.locator('.results-summary')).toHaveText(`${socialHarp.length} matches · ${socialHarp.length} tunes`);
      await expect(page.locator('.result-row')).toHaveCount(Math.min(80, socialHarp.length));
      await expect(page.getByRole('heading', { name: `${socialHarp[0].songNo} — ${socialHarp[0].title}`, exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Clear filters', exact: true })).toHaveCount(0);
      await expect(page.locator('vite-error-overlay')).toHaveCount(0);
      expect(errors).toEqual([]);
      if (facet === 'Key filter') {
        await page.screenshot({ path: process.env.ATLAS_SCREENSHOTS
          ? join(process.env.ATLAS_SCREENSHOTS, `book-filter-${width}.png`)
          : testInfo.outputPath(`book-filter-${width}.png`) });
      }
    });
  }

  test(`changing books preserves available key/part filters and search/sort at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
    await page.goto('/?book=sh1991');
    await page.getByLabel('Key filter', { exact: true }).selectOption('C');
    await page.getByLabel('Available part filter', { exact: true }).selectOption('Treble');
    await page.getByLabel('Sort tunes', { exact: true }).selectOption('title');
    await page.getByTestId('tune-search').fill('Blooming');
    await expect(page.locator('.result-row').first()).toBeVisible();
    await page.getByLabel('Tune book', { exact: true }).selectOption('sh2025');
    await expect(page.getByLabel('Key filter', { exact: true })).toHaveValue('C');
    await expect(page.getByLabel('Available part filter', { exact: true })).toHaveValue('Treble');
    await expect(page.getByLabel('Sort tunes', { exact: true })).toHaveValue('title');
    await expect(page.getByTestId('tune-search')).toHaveValue('Blooming');
    await expect(page.locator('.result-row').first()).toBeVisible();
    expect(errors).toEqual([]);
  });
}
