import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`edition comparison follows split records with keyboard at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/?book=sh1991&tune=' + encodeURIComponent('sh 37t (sh1991) — Ester'));
    const summary = page.locator('.edition-comparison summary');
    await summary.focus();
    await page.keyboard.press('Enter');
    const panel = page.locator('.edition-comparison');
    await expect(panel).toContainText('flags an edition change');
    const link = panel.getByRole('link', { name: 'Open Sacred Harp 2025 record', exact: true });
    await expect(link).toHaveAttribute('href', /book=sh2025/);
    await link.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByLabel('Tune book', { exact: true })).toHaveValue('sh2025');
    await expect(page.locator('.first-line')).toContainText('Awake');
    expect(new URL(page.url()).searchParams.get('tune')).toBe('sh 37t (sh2025) — Ester');
    await page.locator('.edition-comparison summary').click();
    await expect(page.locator('.edition-comparison')).toContainText('Sacred Harp 2025 (selected)');
    await expect(page.locator('.edition-comparison').getByRole('link', { name: 'Open Sacred Harp 1991 record', exact: true })).toBeVisible();
    const bounds = await page.locator('.edition-comparison').boundingBox();
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `work/browser-tests/edition-comparison-${width}.png` });
    expect(errors).toEqual([]);
  });
}

test('unlisted changes do not claim equal music and unrelated tunes have no panel', async ({ page }) => {
  await page.goto('/?book=sh2025&tune=' + encodeURIComponent('sh 26 — Samaria'));
  await page.locator('.edition-comparison summary').click();
  await expect(page.locator('.edition-comparison')).toContainText('does not establish identical text or music');
  await expect(page.locator('.edition-comparison')).toContainText('Alternate-edition reference only');
  await page.goto('/?book=kentucky&tune=' + encodeURIComponent('kentucky 10 — New-Salem'));
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
  await expect(page.locator('.edition-comparison')).toHaveCount(0);
});
