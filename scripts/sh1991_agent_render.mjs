#!/usr/bin/env node
/** Offline import/render proof for agent-corrected excerpts, not source recognition. */
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const directory = path.resolve(process.argv[2] || path.join(root, 'work/model-pilot/sh1991-v1/agent-correction-v1-final-20261016'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const manifestBytes = await readFile(path.join(directory, 'render-inputs.json'));
const manifest = JSON.parse(manifestBytes);
const reportBytes = await readFile(path.join(directory, 'report.json'));
const report = JSON.parse(reportBytes);
if (manifest.inputManifestSha256 !== report.inputManifestSha256) throw new Error('Manifest binding drift');
let launchOptions = { headless: true };
try {
  await access(chromium.executablePath());
  launchOptions = { ...launchOptions, channel: 'chromium' };
} catch {
  // Use the installed browser in a fresh, headless profile. No user profile,
  // sign-in, downloads, or browser installation is needed by this local check.
  launchOptions = { ...launchOptions, channel: 'chrome' };
}
const browser = await chromium.launch(launchOptions);
const records = [];
try {
  for (const record of manifest.records) {
    const xml = await readFile(record.path);
    if (hash(xml) !== record.sha256) throw new Error('Excerpt drift');
    const page = await browser.newPage({ viewport: { width: 1200, height: 500 } });
    const errors = [];
    // No network access or remote source assets are needed by this render.
    await page.route('**/*', route => route.abort());
    page.on('pageerror', error => errors.push(String(error)));
    await page.setContent('<!doctype html><meta charset="utf-8"><title>Quarantined pitch/rhythm excerpt</title><h1 style="font:18px sans-serif"></h1><p style="font:14px sans-serif">Agent repair • opening top staff only • not full-score acceptance</p><div id="score"></div>');
    await page.locator('h1').evaluate((element, label) => { element.textContent = label; }, `${record.songNo} ${record.title}`);
    await page.addScriptTag({ path: path.join(root, 'node_modules/opensheetmusicdisplay/build/opensheetmusicdisplay.min.js') });
    const result = await page.evaluate(async xmlText => {
      const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay('score', {
        autoResize: false, drawTitle: false, drawingParameters: 'compacttight', backend: 'svg',
      });
      await osmd.load(xmlText);
      osmd.render();
      const sheet = osmd.Sheet;
      return { importedMeasures: sheet.SourceMeasures.length,
        importedQuarterDurations: sheet.SourceMeasures.map(m => m.Duration.RealValue * 4),
        svgElements: document.querySelectorAll('#score svg').length };
    }, xml.toString('utf8'));
    const screenshot = path.join(directory, 'render', `${record.songNo}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    const durationMatch = result.importedQuarterDurations.length === record.expectedQuarterDurations.length
      && result.importedQuarterDurations.every((value, i) => Math.abs(value-record.expectedQuarterDurations[i]) < 1e-9);
    records.push({ songNo: record.songNo, excerptSha256: record.sha256, ...result,
      expectedQuarterDurations: record.expectedQuarterDurations, durationMatch, errors,
      screenshot, screenshotSha256: hash(await readFile(screenshot)),
      passed: durationMatch && result.svgElements > 0 && errors.length === 0 });
    await page.close();
  }
} finally {
  await browser.close();
}
const receipt = { implementationSha256: hash(await readFile(fileURLToPath(import.meta.url))),
  renderInputSha256: hash(manifestBytes), repairReportSha256: hash(reportBytes),
  renderer: 'OpenSheetMusicDisplay 2.2.1 / local Chromium; all page network requests blocked',
  browserVersion: browser.version(), browserChannel: launchOptions.channel,
  verificationScope: 'notation import, layout, and measure duration only; not source-fidelity proof',
  safeToPromote: false, sourceCertified: false, humanReviewRequired: false,
  summary: { excerpts: records.length, passed: records.filter(r => r.passed).length }, records };
await mkdir(path.join(directory, 'render'), { recursive: true });
await writeFile(path.join(directory, 'render-receipt.json'), JSON.stringify(receipt, null, 2)+'\n');
console.log(JSON.stringify(receipt.summary));
if (receipt.summary.passed !== records.length) process.exitCode = 1;
