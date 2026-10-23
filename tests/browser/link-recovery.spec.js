import { test, expect } from '@playwright/test';
import { join } from 'node:path';

// Synthetic metadata-only records keep this recovery check independent of
// score availability and source material.
const catalogue = {
  books: { sh1991: { label: 'Recovery book A' }, sh2025: { label: 'Recovery book B' } },
  songs: [
    { id: 'recovery-a', songNo: '1', title: 'Recovery Alpha', books: ['sh1991'] },
    { id: 'recovery-b', songNo: '2', title: 'Recovery Beta', books: ['sh1991'] },
    { id: 'recovery-c', songNo: '3', title: 'Recovery Gamma', books: ['sh2025'] },
  ],
  coverage: { byBook: {} },
};
const missingTune = 'This tune link does not match a record in this edition. Search for the tune or choose another book.';
const unknownBook = 'This tune link names an unknown book. Choose a book to continue.';

async function prepare(page, width) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (['error', 'warning'].includes(message.type()) && !/Failed to load resource|net::ERR/.test(message.text())) errors.push(message.text());
  });
  // External fonts and source sites do not participate in this local flow.
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
  await page.route('**/reader-data/catalogue.json', route => route.fulfill({ json: catalogue }));
  await page.route('**/human-review-queue.json', route => route.fulfill({ json: { reviewNow: [] } }));
  await page.route('**/source-health.json', route => route.fulfill({ json: { records: [] } }));
  return errors;
}

async function screenshot(page, testInfo, name) {
  await page.screenshot({ path: process.env.ATLAS_SCREENSHOTS
    ? join(process.env.ATLAS_SCREENSHOTS, name)
    : testInfo.outputPath(name) });
}

for (const width of [1440, 390]) {
  for (const [name, path] of [
    ['unknown-tune', '/?book=sh1991&tune=not-a-record'],
    ['book-only', '/?book=sh1991'],
  ]) {
    test(`selecting a tune clears the ${name} notice at ${width}px`, async ({ page }, testInfo) => {
      const errors = await prepare(page, width);
      await page.goto(path);
      await expect(page).toHaveTitle('The Shape-Note Atlas');
      await expect(page.getByRole('status').filter({ hasText: missingTune })).toBeVisible();
      await page.getByTestId('tune-search').fill('Recovery Beta');
      await expect(page.locator('.result-row')).toHaveCount(1);
      // Filtering and its automatic selection do not dismiss link errors.
      // The explicit recovery choice below does, including an already-selected row.
      await expect(page.getByRole('status').filter({ hasText: missingTune })).toBeVisible();
      await screenshot(page, testInfo, `${name}-before-${width}.png`);
      await page.getByRole('button', { name: /2 Recovery Beta/ }).click();
      await expect(page.getByRole('heading', { name: '2 — Recovery Beta', exact: true })).toBeVisible();
      if (width === 390) await expect(page.locator('#selected-tune-details')).toBeFocused();
      await screenshot(page, testInfo, `${name}-after-${width}.png`);
      await expect(page.getByRole('status').filter({ hasText: missingTune })).toHaveCount(0);
      await expect(page.locator('vite-error-overlay')).toHaveCount(0);
      expect(errors).toEqual([]);
    });
  }

  test(`choosing a book clears an unknown-book notice at ${width}px`, async ({ page }, testInfo) => {
    const errors = await prepare(page, width);
    await page.goto('/?book=not-a-book&tune=not-a-record');
    await expect(page.getByRole('status').filter({ hasText: unknownBook })).toBeVisible();
    await page.getByLabel('Tune book', { exact: true }).selectOption('sh2025');
    await expect(page.getByRole('heading', { name: '3 — Recovery Gamma', exact: true })).toBeVisible();
    await expect(page.getByRole('status').filter({ hasText: unknownBook })).toHaveCount(0);
    await screenshot(page, testInfo, `book-recovery-${width}.png`);
    expect(errors).toEqual([]);
  });

  test(`a valid tune link opens without a recovery notice at ${width}px`, async ({ page }) => {
    const errors = await prepare(page, width);
    await page.goto('/?book=sh1991&tune=recovery-b');
    await expect(page.getByRole('heading', { name: '2 — Recovery Beta', exact: true })).toBeVisible();
    await expect(page.getByRole('status').filter({ hasText: /This tune link/ })).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
