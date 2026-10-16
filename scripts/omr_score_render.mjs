#!/usr/bin/env node
/** Offline full-score import/layout receipt, never source-fidelity proof. */
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = path.resolve(process.argv[2]);
const manifestBytes = await readFile(manifestPath);
const manifest = JSON.parse(manifestBytes);
const hash = data => createHash('sha256').update(data).digest('hex');
const directory = path.dirname(manifestPath);
await mkdir(path.join(directory, 'render'), { recursive: true });
const options = { headless: true };
try { await access(chromium.executablePath()); options.channel = 'chromium'; }
catch { options.channel = 'chrome'; }
const browser = await chromium.launch(options);
const records = [];
try {
  for (const record of manifest.records) {
    const xml = await readFile(path.resolve(root, record.xmlPath));
    const report = await readFile(path.resolve(root, record.reportPath));
    if (hash(xml) !== record.xmlSha256 || hash(report) !== record.reportSha256) {
      throw new Error('Frozen render input/report drift');
    }
    const page = await browser.newPage({ viewport: { width: 1500, height: 900 } });
    const errors = [];
    await page.route('**/*', route => route.abort());
    page.on('pageerror', error => errors.push(String(error)));
    await page.setContent('<!doctype html><meta charset="utf-8"><title>Quarantined source repair</title><h1 style="font:20px system-ui"></h1><p style="font:14px system-ui">Full written pitch/rhythm grid; other fields unresolved. Not a certified score.</p><main id="score"></main>');
    await page.locator('h1').evaluate((element, title) => { element.textContent = title; }, record.label);
    await page.addScriptTag({ path: path.join(root, 'node_modules/opensheetmusicdisplay/build/opensheetmusicdisplay.min.js') });
    let imported;
    try {
      imported = await page.evaluate(async text => {
        const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay('score', {
          autoResize: false, drawTitle: false, drawingParameters: 'compacttight', backend: 'svg',
        });
        await osmd.load(text);
        osmd.render();
        return { measures: osmd.Sheet.SourceMeasures.length,
          quarterDurations: osmd.Sheet.SourceMeasures.map(m => m.Duration.RealValue * 4),
          svgElements: document.querySelectorAll('#score svg').length };
      }, xml.toString('utf8'));
    } catch (error) { errors.push(String(error)); }
    const screenshot = path.join(directory, 'render', `${record.id}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    const durationMatch = !!imported && imported.quarterDurations.length === record.expectedQuarterDurations.length
      && imported.quarterDurations.every((d, i) => Math.abs(d-record.expectedQuarterDurations[i]) < 1e-9);
    records.push({ id: record.id, ...imported, durationMatch, errors,
      screenshot: path.relative(root, screenshot), screenshotSha256: hash(await readFile(screenshot)),
      passed: durationMatch && imported.svgElements > 0 && errors.length === 0 });
    await page.close();
  }
} finally { await browser.close(); }
const receipt = { manifestSha256: hash(manifestBytes), implementationSha256: hash(await readFile(fileURLToPath(import.meta.url))),
  browserChannel: options.channel, scope: 'Full-score import, layout and measure durations only; not source fidelity.',
  sourceCertified: false, safeToPromote: false, records,
  summary: { scores: records.length, passed: records.filter(r => r.passed).length } };
await writeFile(path.join(directory, 'render-receipt.json'), JSON.stringify(receipt, null, 2)+'\n');
console.log(JSON.stringify(receipt.summary));
if (receipt.summary.passed !== records.length) process.exitCode = 1;
