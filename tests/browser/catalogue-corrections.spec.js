import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`source-backed catalogue corrections at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/?book=kentucky&tune=kentucky%2010%20%E2%80%94%20New-Salem');
    await expect(page).toHaveTitle('The Shape-Note Atlas');
    await page.getByTestId('tune-search').fill('O thou in whose presence');
    await expect(page.locator('.results-list .result-row')).toHaveCount(1);
    await expect(page.locator('.result-row')).toContainText('O thou in whose presence my soul takes delight,');
    await page.locator('.result-row').click();
    await expect(page.locator('.first-line')).toContainText('O thou in whose presence my soul takes delight,');
    await page.screenshot({ path: `/tmp/atlas-metadata-evidence/new-salem-${width}.png`, fullPage: false });
    await page.goto('/?book=sacredharptunes&tune=' + encodeURIComponent('sacredharptunes a-glimpse-of-thee — A Glimpse of Thee L.M.'));
    await expect(page.getByRole('heading', { name: 'a-glimpse-of-thee — A Glimpse of Thee L.M.D.', exact: true })).toBeVisible();
    await page.getByTestId('tune-search').fill('Glimpse of Thee L.M.D.');
    await expect(page.locator('.result-row')).toHaveCount(1);
    await expect(page.locator('.result-row')).toContainText('L.M.D.');
    await page.screenshot({ path: `/tmp/atlas-metadata-evidence/glimpse-${width}.png`, fullPage: false });
    await expect(page.locator('vite-error-overlay')).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
