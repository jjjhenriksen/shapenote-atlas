import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { join } from 'node:path';

const committed = JSON.parse(readFileSync(new URL('../../public/corpus.json', import.meta.url)));
function fixture(length = 4) {
  const score = (id) => ({ sourceUrl: `https://example.invalid/${id}`, scoreRef: `/fixture-${id}.json`, keySignature: '0:major', parts: ['Treble', 'Alto', 'Tenor', 'Bass'].map((name) => ({ name, events: Array.from({ length }, (_, onset) => ({ onset, beats: 1, step: 'C', octave: 4, measure: onset + 1, type: 'quarter' })) })), transposition: { available: true } });
  const songs = ['a', 'b'].map((id, i) => ({ id, title: `Fixture ${id.toUpperCase()}`, songNo: String(i + 1), books: ['sh1991'], urls: [`https://example.invalid/${id}`], metadataByBook: { sh1991: { keySignature: '0:major' } }, scoreByBook: { sh1991: score(id) } }));
  return { books: { sh1991: committed.books.sh1991 }, songs, coverage: { byBook: {} } };
}
async function intercept(page, data = fixture()) {
  await page.route('**/corpus.json', (route) => route.fulfill({ json: data }));
  await page.route('**/human-review-queue.json', (route) => route.fulfill({ json: { reviewNow: [] } }));
  await page.route('**/source-health.json', (route) => route.fulfill({ json: { records: [{ url: 'https://example.invalid/a', status: 'reachable' }] } }));
  await page.route('**/fixture-*.json', (route) => { const id = /fixture-(.).json/.exec(route.request().url())[1]; return route.fulfill({ json: data.songs.find((song) => song.id === id).scoreByBook.sh1991 }); });
}
async function open(page) {
  await page.goto('/?book=sh1991&tune=a');
  await expect(page.getByRole('heading', { name: '1 — Fixture A', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
}
async function unmount(page) { await page.evaluate(async () => { const module = await import(document.querySelector('script[src*="/src/main.jsx"]').src); module.atlasRoot.unmount(); }); }

async function mockAudio(page, pending = false) {
  await page.addInitScript(({ pending }) => {
    const intervals = new Set(), timeouts = new Set();
    const setInterval = window.setInterval, clearInterval = window.clearInterval, setTimeout = window.setTimeout, clearTimeout = window.clearTimeout;
    window.setInterval = (...args) => { const id = setInterval(...args); if ([25, 100].includes(args[1])) intervals.add(id); return id; };
    window.clearInterval = (id) => { intervals.delete(id); clearInterval(id); };
    window.setTimeout = (fn, ms, ...args) => { const id = setTimeout(() => { timeouts.delete(id); fn(...args); }, ms); if (ms === 2600) timeouts.add(id); return id; };
    window.clearTimeout = (id) => { timeouts.delete(id); clearTimeout(id); };
    const trace = window.__audio = { contexts: [], nodes: [], oscillators: [], intervals, timeouts, pending };
    const parameter = () => ({ value: 0, setValueAtTime() {}, linearRampToValueAtTime() {}, setTargetAtTime() {} });
    class Node { constructor() { this.disconnected = false; trace.nodes.push(this); } connect() {} disconnect() { this.disconnected = true; } }
    class Audio {
      constructor() { this.state = pending ? 'suspended' : 'running'; this.currentTime = 0; this.destination = {}; this.closeCalls = 0; trace.contexts.push(this); }
      createGain() { const node = new Node(); node.gain = parameter(); return node; }
      createStereoPanner() { const node = new Node(); node.pan = parameter(); return node; }
      createOscillator() { const node = new Node(); node.frequency = parameter(); node.stops = []; node.start = (at) => node.startAt = at; node.stop = (at) => node.stops.push(at); trace.oscillators.push(node); return node; }
      resume() { if (pending) return new Promise((resolve) => trace.resolveResume = () => { this.state = 'running'; resolve(); }); this.state = 'running'; return Promise.resolve(); }
      suspend() { this.state = 'suspended'; return Promise.resolve(); }
      close() { this.state = 'closed'; this.closeCalls++; return Promise.resolve(); }
    }
    window.AudioContext = Audio;
  }, { pending });
}

for (const [name, payload] of Object.entries({ missingSongs: { books: fixture().books }, wrongSongs: { ...fixture(), songs: {} }, wrongBooks: { ...fixture(), books: [] }, missingBooks: { songs: [] } })) {
  test(`malformed corpus ${name} recovers through retry`, async ({ page }) => {
    const errors = []; page.on('pageerror', (error) => errors.push(error.message));
    await intercept(page); let calls = 0;
    await page.route('**/corpus.json', (route) => route.fulfill({ json: ++calls === 1 ? payload : fixture() }));
    await page.goto('/?book=sh1991&tune=a');
    await expect(page.getByRole('alert')).toContainText('incompatible');
    await page.getByRole('button', { name: 'Retry loading', exact: true }).click();
    await expect(page.getByRole('heading', { name: '1 — Fixture A' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
    expect(errors).toEqual([]);
  });
}

test('source health failure, loading, retry success preserve the selected tune', async ({ page }) => {
  await intercept(page); let calls = 0, finish;
  await page.route('**/source-health.json', async (route) => {
    if (++calls === 1) return route.fulfill({ status: 503 });
    await new Promise((resolve) => finish = resolve);
    return route.fulfill({ json: { records: [{ url: 'https://example.invalid/b', status: 'reachable' }] } });
  });
  await open(page);
  await page.getByRole('button', { name: /Fixture B/ }).click();
  await expect(page.getByLabel('Source health', { exact: true })).toContainText('unavailable');
  if (process.env.ATLAS_SCREENSHOTS) await page.getByLabel('Source health', { exact: true }).screenshot({ path: join(process.env.ATLAS_SCREENSHOTS, 'source-health-retry.png') });
  await page.getByRole('button', { name: 'Retry source health', exact: true }).click();
  await expect(page.getByLabel('Source health', { exact: true })).toContainText('Loading source health');
  await expect.poll(() => Boolean(finish)).toBe(true); finish();
  await expect(page.getByLabel('Source health', { exact: true })).toContainText('1 reachable');
  await expect(page.getByRole('heading', { name: '2 — Fixture B', exact: true })).toBeVisible();
});

test('play and toast then unmount stop chains, close context and clear timers; remount works', async ({ page }) => {
  await mockAudio(page); await intercept(page); await open(page);
  await page.getByRole('button', { name: 'Show source preservation note' }).click();
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await unmount(page);
  expect(await page.evaluate(() => ({ intervals: __audio.intervals.size, timeouts: __audio.timeouts.size, closes: __audio.contexts[0].closeCalls, connected: __audio.nodes.filter((node) => !node.disconnected).length, stopped: __audio.oscillators.every((node) => node.stops.includes(undefined)) }))).toEqual({ intervals: 0, timeouts: 0, closes: 1, connected: 0, stopped: true });
  await page.evaluate(async () => { const module = await import(document.querySelector('script[src*="/src/main.jsx"]').src); window.__remount = module.mountAtlas(document.getElementById('root')); });
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await page.evaluate(() => __remount.unmount());
  expect(await page.evaluate(() => __audio.contexts.map((context) => context.closeCalls))).toEqual([1, 1]);
});

test('a pending audio resume cannot create playback or timers after disposal', async ({ page }) => {
  await mockAudio(page, true); await intercept(page); await open(page);
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Boolean(__audio.resolveResume))).toBe(true);
  await unmount(page);
  await page.evaluate(() => __audio.resolveResume());
  expect(await page.evaluate(() => ({ oscillators: __audio.oscillators.length, intervals: __audio.intervals.size, closed: __audio.contexts[0].closeCalls }))).toEqual({ oscillators: 0, intervals: 0, closed: 1 });
});

test('long-score start stays bounded and stop/settings/navigation remain responsive', async ({ page }) => {
  await mockAudio(page); await intercept(page, fixture(200)); await open(page);
  await page.getByLabel('Playback loops', { exact: true }).selectOption('8');
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  expect(await page.evaluate(() => __audio.oscillators.length)).toBe(4);
  const start = Date.now(); await page.getByRole('button', { name: 'Stop', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeVisible();
  expect(Date.now() - start).toBeLessThan(1500);
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await page.getByLabel('Tempo BPM', { exact: true }).fill('120');
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeVisible();
  expect(await page.evaluate(() => __audio.intervals.size)).toBe(0);
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await page.getByRole('button', { name: /Fixture B/ }).click();
  await expect(page.getByRole('heading', { name: '2 — Fixture B' })).toBeVisible();
  expect(await page.evaluate(() => __audio.nodes.every((node) => node.disconnected))).toBe(true);
});

// Use a real streaming HTTP body so cancellation proves the obsolete download
// closes, rather than only suppressing a React state update.
test('rapid score navigation cancels streaming bodies and retry commits only current score', async ({ page }) => {
  const data = fixture(); const aborted = new Set(); const begun = new Set(); const responses = new Map(); let attempts = 0;
  const server = createServer((request, response) => {
    response.setHeader('Access-Control-Allow-Origin', '*'); response.setHeader('Content-Type', 'application/json');
    const id = request.url.slice(1); begun.add(id);
    if (id === 'b' && ++attempts === 1) { response.writeHead(503); response.end('unavailable'); return; }
    response.writeHead(200); response.write('{'); responses.set(id, response);
    response.on('close', () => { if (!response.writableEnded) aborted.add(id); });
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  data.songs.forEach((song) => song.scoreByBook.sh1991.scoreRef = `${origin}/${song.id}`);
  try {
    await intercept(page, data); await page.goto('/?book=sh1991&tune=a');
    await expect.poll(() => begun.has('a')).toBe(true);
    await page.getByRole('button', { name: /Fixture B/ }).click();
    await expect.poll(() => aborted.has('a')).toBe(true);
    await page.getByRole('button', { name: 'Retry loading', exact: true }).click();
    await expect.poll(() => attempts).toBe(2);
    await page.getByRole('button', { name: /Fixture A/ }).click();
    await expect.poll(() => aborted.has('b')).toBe(true);
    await expect.poll(() => responses.get('a') && !responses.get('a').destroyed).toBe(true);
    responses.get('a').end(JSON.stringify(data.songs[0].scoreByBook.sh1991).slice(1));
    await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeEnabled();
    await expect(page.getByRole('heading', { name: '1 — Fixture A' })).toBeVisible();
    expect(await page.getByRole('alert').count()).toBe(0);
  } finally { for (const response of responses.values()) response.destroy(); await new Promise((resolve) => server.close(resolve)); }
});

test('unmount aborts pending corpus, review queue and health downloads', async ({ page }) => {
  await page.addInitScript(() => {
    const original = window.fetch; window.__requests = [];
    window.fetch = (url, options) => {
      if (!/\/(corpus|human-review-queue|source-health)\.json$/.test(url)) return original(url, options);
      const item = { url, aborted: false }; __requests.push(item);
      return new Promise((resolve, reject) => options?.signal?.addEventListener('abort', () => { item.aborted = true; reject(new DOMException('Aborted', 'AbortError')); }));
    };
  });
  await page.goto('/');
  await expect.poll(() => page.evaluate(() => __requests.length)).toBe(3);
  await unmount(page);
  expect(await page.evaluate(() => __requests.every((item) => item.aborted))).toBe(true);
});

test('real Web Audio progresses, pauses, resumes, transposes and ends automatically', async ({ page }) => {
  const errors = []; page.on('pageerror', (error) => errors.push(error.message));
  await intercept(page, fixture(1)); await open(page);
  await page.getByLabel('Tempo BPM', { exact: true }).fill('220');
  await page.getByLabel('Target key', { exact: true }).selectOption('D');
  await page.getByRole('button', { name: 'Play song', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  await page.waitForTimeout(900);
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Play song', exact: true })).toBeVisible();
  await expect(page.getByLabel('Playback progress 0 percent')).toBeVisible();
  expect(errors).toEqual([]);
});
