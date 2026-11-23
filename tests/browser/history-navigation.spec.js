import { test, expect } from '@playwright/test';

// These synthetic records deliberately disagree on every discovery facet.
// No source notation or catalogue mapping is changed by this navigation test.
const score = (id, keySignature, name, available) => ({
  sourceUrl: `https://example.invalid/${id}`, scoreRef: `/history-score-${id}.json`, keySignature,
  parts: [{ name, events: [{ onset: 0, beats: 32, step: 'C', octave: 4, measure: 1, type: 'whole' }] }],
  transposition: { available },
});
const songs = [
  { id: 'history-a', songNo: '1', title: 'History Alpha', books: ['sh1991'], scoreByBook: { sh1991: score('a', 'C major', 'Treble', true) } },
  { id: 'history-b', songNo: '2', title: 'History Beta', books: ['sh1991'], scoreByBook: { sh1991: score('b', 'D minor', 'Bass', false) } },
  { id: 'history-c', songNo: '3', title: 'History Gamma', books: ['sh2025'] },
];
const catalogue = { books: { sh1991: { label: 'History book A' }, sh2025: { label: 'History book B' } }, songs, coverage: { byBook: {} } };

async function prepare(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
  await page.route('**/reader-data/catalogue.json', route => route.fulfill({ json: catalogue }));
  await page.route('**/human-review-queue.json', route => route.fulfill({ json: { reviewNow: [] } }));
  await page.route('**/source-health.json', route => route.fulfill({ json: { records: [] } }));
  await page.route('**/history-score-*.json', route => {
    const id = /history-score-(.).json/.exec(route.request().url())[1];
    return route.fulfill({ json: songs.find(song => song.id === `history-${id}`).scoreByBook.sh1991 });
  });
  return errors;
}

async function pushTune(page, book, tune) {
  await page.evaluate(({ book, tune }) => {
    history.pushState({}, '', `?book=${book}&tune=${tune}`);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, { book, tune });
}

for (const [label, value] of [['Key filter', 'C'], ['Mode filter', 'major'], ['Available part filter', 'Treble'], ['Transposable', true]]) {
  test(`Back and Forward restore the linked record after the ${label} facet`, async ({ page }) => {
    const errors = await prepare(page);
    await page.goto('/?book=sh1991&tune=history-b');
    await expect(page.getByRole('heading', { name: '2 — History Beta', exact: true })).toBeVisible();
    await pushTune(page, 'sh1991', 'history-a');
    await expect(page.getByRole('heading', { name: '1 — History Alpha', exact: true })).toBeVisible();
    if (value === true) await page.getByLabel(label, { exact: true }).check();
    else await page.getByLabel(label, { exact: true }).selectOption(value);
    await expect(page.locator('.result-row')).toHaveCount(1);
    await page.goBack();
    await expect(page).toHaveURL(/tune=history-b/);
    await expect(page.getByRole('heading', { name: '2 — History Beta', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
    await expect(page.locator('.result-row[aria-current="true"]')).toContainText('History Beta');
    await expect(page.locator('.result-row')).toHaveCount(2);
    await expect(page.getByRole('button', { name: 'Clear filters', exact: true })).toHaveCount(0);
    await page.goForward();
    await expect(page).toHaveURL(/tune=history-a/);
    await expect(page.getByRole('heading', { name: '1 — History Alpha', exact: true })).toBeVisible();
    await expect(page.locator('vite-error-overlay')).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

test('history restores a metadata-only edition from filtered practice on a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors = await prepare(page);
  await page.goto('/?book=sh2025&tune=history-c');
  await expect(page.getByRole('heading', { name: '3 — History Gamma', exact: true })).toBeVisible();
  await pushTune(page, 'sh1991', 'history-a');
  await page.getByRole('button', { name: 'Practice', exact: true }).click();
  await page.getByLabel('Key filter', { exact: true }).selectOption('C');
  await page.getByLabel('Mode filter', { exact: true }).selectOption('major');
  await page.getByLabel('Available part filter', { exact: true }).selectOption('Treble');
  await page.getByLabel('Transposable', { exact: true }).check();
  await page.goBack();
  await expect(page.getByLabel('Tune book', { exact: true })).toHaveValue('sh2025');
  await expect(page.getByRole('heading', { name: '3 — History Gamma', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Library', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('.result-row')).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Clear filters', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('history stops playback and keeps the linked selection through delayed detail loading', async ({ page }) => {
  const errors = await prepare(page);
  const delayed = structuredClone(catalogue);
  delayed.songs[1].detailRef = '/history-detail-b.json';
  await page.route('**/reader-data/catalogue.json', route => route.fulfill({ json: delayed }));
  let requests = 0;
  let releaseDetail;
  await page.route('**/history-detail-b.json', async route => {
    if (++requests === 2) await new Promise(resolve => { releaseDetail = resolve; });
    await route.fulfill({ json: {
      song: { ...songs[1], rawFirstLine: 'The linked detail has arrived' },
      reviewQueue: { reviewNow: [] }, sourceHealth: { records: [] },
    } });
  });
  await page.goto('/?book=sh1991&tune=history-b');
  await expect(page.locator('.first-line')).toContainText('The linked detail has arrived');
  await pushTune(page, 'sh1991', 'history-a');
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
  await page.getByLabel('Key filter', { exact: true }).selectOption('C');
  await page.getByLabel('Target key', { exact: true }).selectOption('D');
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await page.goBack();
  await expect.poll(() => Boolean(releaseDetail)).toBe(true);
  await expect(page.getByRole('heading', { name: '2 — History Beta', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toHaveCount(0);
  releaseDetail();
  await expect(page.locator('.first-line')).toContainText('The linked detail has arrived');
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
  await expect(page.getByLabel('Target key', { exact: true })).toHaveValue('');
  await expect(page.locator('.key-tag')).toContainText('D minor');
  await expect(page.locator('.result-row[aria-current="true"]')).toContainText('History Beta');
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`pagination brings the first new result into view without selecting it at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    const errors = await prepare(page);
    const paginated = { ...catalogue, songs: Array.from({ length: 161 }, (_, index) => ({
      id: `page-${index + 1}`, songNo: String(index + 1), title: `Page tune ${index + 1}`, books: ['sh1991'],
    })) };
    await page.route('**/reader-data/catalogue.json', route => route.fulfill({ json: paginated }));
    await page.goto('/?book=sh1991&tune=page-1');
    const next = page.getByRole('button', { name: 'Next', exact: true });
    const previous = page.getByRole('button', { name: 'Previous', exact: true });
    await expect(previous).toBeDisabled();
    await next.scrollIntoViewIfNeeded();
    await next.focus();
    await page.keyboard.press('Enter');
    const first = page.locator('.result-row').first();
    await expect(first).toContainText('Page tune 81');
    await expect(first).toBeFocused();
    await expect(first).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole('heading', { name: '1 — Page tune 1', exact: true })).toBeAttached();
    await next.click();
    await expect(first).toContainText('Page tune 161');
    await expect(first).toBeFocused();
    await expect(first).toBeInViewport({ ratio: 1 });
    await expect(next).toBeDisabled();
    await previous.click();
    await expect(first).toContainText('Page tune 81');
    await expect(first).toBeFocused();
    await expect(first).toBeInViewport({ ratio: 1 });
    await expect(page.getByRole('heading', { name: '1 — Page tune 1', exact: true })).toBeAttached();
    expect(errors).toEqual([]);
  });
}
