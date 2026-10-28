#!/usr/bin/env node
// Matched, sequential, cold-browser production comparison. No app instrumentation required.
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync, writeFileSync, mkdirSync, symlinkSync, existsSync } from 'node:fs';
import { resolve, dirname, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';
import { cpus, platform, release } from 'node:os';
import { chromium } from 'playwright';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const option = (key, fallback) => {
  const index = args.indexOf(`--${key}`);
  if (index < 0) return fallback;
  if (!args[index + 1] || args[index + 1].startsWith('--')) throw Error(`Missing --${key} value`);
  return args[index + 1];
};
const runs = Number(option('runs', '5'));
if (!Number.isInteger(runs) || runs < 1) throw Error('--runs must be a positive integer');
const out = resolve(option('out', `/tmp/atlas-reader-benchmark-${Date.now()}`));
const git = (...values) => execFileSync('git', values, { cwd: repo, encoding: 'utf8' }).trim();
const revisions = { before: git('rev-parse', `${option('before', 'HEAD^')}^{commit}`), after: git('rev-parse', `${option('after', 'HEAD')}^{commit}`) };
const profiles = [
  { name: 'desktop', viewport: { width: 1440, height: 1000 } },
  { name: 'mobile-viewport', viewport: { width: 390, height: 844 } },
];
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
const network = { offline: false, latency: 150, downloadThroughput: 200000, uploadThroughput: 93750 };
const route = '/?book=kentucky&tune=kentucky%2010%20%E2%80%94%20New-Salem';
mkdirSync(out, { recursive: true });
const save = (name, data) => writeFileSync(resolve(out, name), JSON.stringify(data, null, 2) + '\n');

function build(label) {
  const dir = resolve(out, label);
  if (args.includes('--reuse-builds')) {
    if (readFileSync(resolve(dir, 'revision.txt'), 'utf8').trim() !== revisions[label]) throw Error(`Reused ${label} revision mismatch`);
    if (!existsSync(resolve(dir, 'dist/index.html'))) throw Error(`Missing ${label} build`);
    return dir;
  }
  if (existsSync(dir)) throw Error(`Build directory exists: ${dir}; use a fresh --out or --reuse-builds`);
  mkdirSync(dir);
  // Archive exact committed content, never the caller's uncommitted workspace.
  const archive = resolve(out, `${label}.tar`);
  execFileSync('git', ['archive', '--format=tar', '-o', archive, revisions[label]], { cwd: repo });
  execFileSync('tar', ['-xf', archive, '-C', dir]);
  if (readFileSync(resolve(dir, 'package-lock.json'), 'utf8') !== readFileSync(resolve(repo, 'package-lock.json'), 'utf8')) {
    throw Error('Dependency lock differs: install matching dependencies in an isolated checkout before comparing');
  }
  symlinkSync(resolve(repo, 'node_modules'), resolve(dir, 'node_modules'), 'dir');
  const log = execFileSync('npm', ['run', 'build'], { cwd: dir, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  writeFileSync(resolve(out, `${label}-build.log`), log);
  writeFileSync(resolve(dir, 'revision.txt'), revisions[label] + '\n');
  return dir;
}

async function serve(dir) {
  const root = resolve(dir, 'dist');
  const cache = new Map();
  const server = createServer((req, res) => {
    try {
      const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      let file = resolve(root, '.' + pathname);
      if (file !== root && !file.startsWith(root + sep)) { res.writeHead(403).end(); return; }
      if (pathname.endsWith('/')) file = resolve(file, 'index.html');
      let entry = cache.get(file);
      if (!entry) {
        const body = readFileSync(file);
        entry = { plain: body, gzip: gzipSync(body, { level: 6 }) };
        cache.set(file, entry);
      }
      const compressed = /gzip/.test(req.headers['accept-encoding'] || '');
      const body = compressed ? entry.gzip : entry.plain;
      res.writeHead(200, { 'Content-Type': mime[extname(file)] || 'application/octet-stream', 'Content-Length': body.length,
        'Cache-Control': 'no-store', 'Vary': 'Accept-Encoding', ...(compressed ? { 'Content-Encoding': 'gzip' } : {}) });
      res.end(body);
    } catch { res.writeHead(404).end('Not found'); }
  });
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  return { server, origin: `http://127.0.0.1:${server.address().port}` };
}

async function sample(browser, origin, profile, measured, shot) {
  const context = await browser.newContext({ viewport: profile.viewport, serviceWorkers: 'block' });
  try {
    const page = await context.newPage();
    const errors = [], failedRequests = [], responses = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', msg => { if (msg.type() === 'error' && !/ERR_BLOCKED_BY_CLIENT/.test(msg.text())) errors.push(msg.text()); });
    page.on('response', response => { if (response.url().startsWith(origin) && response.status() >= 400) responses.push({ url: response.url(), status: response.status() }); });
    page.on('requestfailed', request => { if (request.url().startsWith(origin)) failedRequests.push({ url: request.url(), error: request.failure() }); });
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    // Same remote-font/source isolation for both builds. No request interception or mocked app data.
    await cdp.send('Network.setBlockedURLs', { urls: ['https://*'] });
    if (measured) {
      await cdp.send('Network.emulateNetworkConditions', network);
      await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    }
    await page.addInitScript(() => {
      performance.setResourceTimingBufferSize(2000);
      window.__benchmark = {};
      const visible = el => el && el.getClientRects().length > 0;
      const tick = () => {
        const heading = [...document.querySelectorAll('.detail-header h2')].find(el => el.textContent.trim() === '10 — New-Salem');
        if (!__benchmark.catalogueMs && visible(heading) && visible(document.querySelector('.results-list .result-row'))) __benchmark.catalogueMs = performance.now();
        const button = [...document.querySelectorAll('button')].find(el => el.textContent.trim() === 'Play song');
        if (!__benchmark.playableMs && visible(button) && !button.disabled) {
          __benchmark.playableMs = performance.now();
          __benchmark.resourcesAtPlayable = performance.getEntriesByType('resource').map(({ name, encodedBodySize, decodedBodySize, transferSize, duration }) => ({ name, encodedBodySize, decodedBodySize, transferSize, duration }));
        }
        if (!__benchmark.catalogueMs || !__benchmark.playableMs) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.goto(origin + route, { waitUntil: 'domcontentloaded', timeout: 180000 });
    await page.waitForFunction(() => __benchmark.catalogueMs && __benchmark.playableMs, null, { timeout: 180000 });
    const result = await page.evaluate(() => ({ ...__benchmark, title: document.title, url: location.href }));
    if (result.title !== 'The Shape-Note Atlas' || await page.locator('vite-error-overlay').count()) throw Error('Page identity/overlay failed');
    await page.locator('.score-engraving[data-render-state="ready"]').waitFor({ timeout: 60000 });
    const searchStart = await page.evaluate(() => performance.now());
    await page.getByTestId('tune-search').fill('New-Salem');
    await page.waitForFunction(() => document.querySelectorAll('.results-list .result-row').length === 1 && document.querySelector('.results-list .result-row').textContent.includes('New-Salem'));
    result.searchRoundTripMs = await page.evaluate(start => performance.now() - start, searchStart);
    if (shot) await page.screenshot({ path: resolve(out, shot) });
    result.errors = errors; result.failedRequests = failedRequests; result.httpErrors = responses;
    // The reader intentionally aborts obsolete score fetches as full tune evidence arrives.
    result.abortedRequests = failedRequests.filter(request => request.error?.errorText === 'net::ERR_ABORTED');
    result.pass = !errors.length && !failedRequests.some(request => request.error?.errorText !== 'net::ERR_ABORTED') && !responses.length;
    if (!result.pass) throw Error(`Browser errors: ${JSON.stringify(result)}`);
    return result;
  } finally { await context.close(); }
}

const resume = args.includes('--resume');
const previousMetadata = resume ? JSON.parse(readFileSync(resolve(out, 'metadata.json'), 'utf8')) : null;
const savedSamples = resume ? JSON.parse(readFileSync(resolve(out, 'samples.json'), 'utf8')) : [];
if (resume && (!args.includes('--reuse-builds') || JSON.stringify(previousMetadata.revisions) !== JSON.stringify(revisions) || previousMetadata.runs !== runs)) throw Error('Resume requires matching revisions, runs and --reuse-builds');
if (resume) {
  if (!Array.isArray(savedSamples)) throw Error('Invalid saved samples');
  const identities = new Set();
  for (const item of savedSamples) {
    const key = `${item.label}/${item.profile}/${item.run}`;
    if (!['before', 'after'].includes(item.label) || !profiles.some(profile => profile.name === item.profile)
      || !Number.isInteger(item.run) || item.run < 1 || item.run > runs || item.pass !== true
      || !['catalogueMs', 'playableMs', 'searchRoundTripMs'].every(metric => Number.isFinite(item[metric]) && item[metric] >= 0)
      || !Array.isArray(item.resourcesAtPlayable) || identities.has(key)) throw Error('Invalid or duplicate saved sample');
    identities.add(key);
  }
}
const services = [];
let browser;
save('status.json', { state: 'running', startedAt: new Date().toISOString() });
try {
  for (const label of ['before', 'after']) {
    console.log(`Building ${label}: ${revisions[label]}`);
    services.push({ label, ...await serve(build(label)) });
  }
  browser = await chromium.launch({ channel: option('channel', 'chrome'), headless: true });
  const metadata = { revisions, runs, profiles, network, cpuSlowdown: 4, compression: 'gzip level 6', browser: browser.version(), node: process.version,
    os: `${platform()} ${release()}`, cpu: cpus()[0]?.model, route, cache: 'fresh browser context, HTTP cache disabled, no service workers',
    scope: 'Local production builds; mobile viewport, not mobile hardware; remote HTTPS blocked; server/disk caches warm; no audio or engraving-speed claim.' };
  if (resume && ['browser', 'node', 'os', 'cpu', 'compression', 'profiles', 'network', 'cpuSlowdown', 'route', 'cache', 'scope'].some(key => JSON.stringify(metadata[key]) !== JSON.stringify(previousMetadata[key]))) throw Error('Resume environment mismatch');
  if (!resume) save('metadata.json', metadata);
  // Excluded warmups populate identical server compression caches and browser process/JIT caches.
  for (const service of services) await sample(browser, service.origin, profiles[0], false);
  const samples = [...savedSamples];
  for (const profile of profiles) for (let run = 0; run < runs; run++) {
    // Reverse order every pair to reduce thermal/time/order bias. Never run concurrently.
    for (const service of run % 2 ? [...services].reverse() : services) {
      if (samples.some(item => item.label === service.label && item.profile === profile.name && item.run === run + 1)) continue;
      const result = await sample(browser, service.origin, profile, true, run === 0 ? `${service.label}-${profile.name}.png` : null);
      samples.push({ label: service.label, profile: profile.name, run: run + 1, ...result });
      save('samples.json', samples);
      console.log(`${profile.name} ${run + 1}/${runs} ${service.label}: catalogue ${result.catalogueMs.toFixed(0)}ms; playable ${result.playableMs.toFixed(0)}ms`);
    }
  }
  const stats = values => {
    const sorted = values.toSorted((a, b) => a - b), n = sorted.length;
    return { median: n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2, min: sorted[0], max: sorted[n - 1], p95: sorted[Math.ceil(n * .95) - 1] };
  };
  const summary = profiles.map(profile => {
    const row = { profile: profile.name };
    for (const label of ['before', 'after']) {
      const group = samples.filter(sample => sample.profile === profile.name && sample.label === label);
      row[label] = Object.fromEntries(['catalogueMs', 'playableMs', 'searchRoundTripMs'].map(metric => [metric, stats(group.map(sample => sample[metric]))]));
      row[label].jsonAtPlayable = group[0].resourcesAtPlayable.filter(resource => /\.json(?:\?|$)/.test(resource.name));
    }
    row.medianSpeedup = Object.fromEntries(['catalogueMs', 'playableMs'].map(metric => [metric, row.before[metric].median / row.after[metric].median]));
    return row;
  });
  save('summary.json', summary);
  const report = ['# Reader before/after benchmark', '', `Before: ${revisions.before}`, `After: ${revisions.after}`, '',
    `${runs} cold-browser samples per build per viewport; 1.6 Mbps download, 150 ms latency, 4× CPU slowdown; identical gzip production server.`, '',
    '| Viewport | Metric | Before median (range) | After median (range) | Speedup |', '|---|---|---:|---:|---:|'];
  for (const row of summary) for (const metric of ['catalogueMs', 'playableMs']) {
    const format = value => `${(value.median / 1000).toFixed(2)} s (${(value.min / 1000).toFixed(2)}–${(value.max / 1000).toFixed(2)})`;
    report.push(`| ${row.profile} | ${metric} | ${format(row.before[metric])} | ${format(row.after[metric])} | ${row.medianSpeedup[metric].toFixed(2)}× |`);
  }
  report.push('', 'Catalogue: first animation-frame sample with selected tune heading and a visible catalogue row. Playable: visible enabled Play song button; not first audible sound.',
    '', 'Search round trip includes automation overhead; JSON byte snapshots include only resources completed at playback readiness, not all eventual traffic. See raw samples for individual requests.',
    '', metadata.scope, '', 'Small-sample lab results, not statistical significance or field Core Web Vitals. Every measured sample also checks identity, nonblank content, overlay, application errors, engraving readiness and search results.');
  writeFileSync(resolve(out, 'report.md'), report.join('\n') + '\n');
  save('status.json', { state: 'passed', completedAt: new Date().toISOString(), sampleCount: samples.length });
  console.log(`Results: ${out}/report.md`);
} catch (error) {
  save('status.json', { state: 'failed', error: error.message, failedAt: new Date().toISOString() });
  throw error;
} finally {
  if (browser) await browser.close();
  for (const service of services) service.server.close();
}
