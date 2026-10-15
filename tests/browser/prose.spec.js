import { test, expect } from '@playwright/test';

const articles = [
  ['trumpet p139 — Three', 139],
  ['trumpet p187 — By Thomas B', 187],
  ['trumpet p265 — Sacred b aLLs Town', 265],
];

for (const width of [1440, 390]) {
  test(`Trumpet articles preserve links without becoming notation gaps at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // Test the reader and its exact destination, not remote PDF rendering.
    await page.route('https://www.singthetrumpet.com/**', route => route.abort());
    for (const [id, leaf] of articles) {
      await page.goto('/?book=trumpet&tune=' + encodeURIComponent(id));
      await expect(page).toHaveTitle('The Shape-Note Atlas');
      await expect(page.getByRole('heading', { name: 'Prose article — no score expected', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Link to this article', exact: true })).toHaveAttribute('href', /book=trumpet/);
      await expect(page.locator('iframe')).toHaveAttribute('src', new RegExp(`#page=${leaf}$`));
      await expect(page.getByRole('button', { name: 'Play song', exact: true })).toHaveCount(0);
    }
    await expect(page.locator('.results-summary')).toHaveText('105 matches · 102 tunes · 3 articles');
    await page.getByLabel('Notation availability').selectOption('prose');
    await expect(page.locator('.result-row')).toHaveCount(3);
    await page.getByTestId('tune-search').fill('Nehemiah Shumway');
    await expect(page.locator('.result-row')).toHaveCount(1);
    await page.locator('.result-row').click();
    await expect(page.getByRole('heading', { name: 'p265 — Article: Old Paths: Nehemiah Shumway', exact: true })).toBeVisible();
    await page.getByTestId('tune-search').fill('');
    await page.getByLabel('Notation availability').selectOption('source-only');
    await expect(page.locator('.results-summary')).toHaveText('102 matches · 102 tunes · 3 articles');
    await expect(page.locator('.result-row').filter({ hasText: 'Article:' })).toHaveCount(0);
    await expect(page.locator('vite-error-overlay')).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
