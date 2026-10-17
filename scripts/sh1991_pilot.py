#!/usr/bin/env python3
"""Local-only SH1991 OMR pilot. Candidate labels never imply source certification."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK = ROOT / 'work/model-pilot/sh1991-v1'
SEED = 'atlas-sh1991-pitch-rhythm-v1'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def now():
    return datetime.now(timezone.utc).isoformat()

def score(data):
    """Written-order events in quarter notes; no inferred mode, lyrics or shapes."""
    if data[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            target = next(x.attrib['full-path'] for x in container.iter() if x.tag.rsplit('}', 1)[-1] == 'rootfile')
            member = archive.getinfo(target)
            if member.file_size > 20_000_000: raise ValueError('oversized score XML')
            data = archive.read(target)
    root = ET.fromstring(data)
    for item in root.iter(): item.tag = item.tag.rsplit('}', 1)[-1]
    if root.tag != 'score-partwise': raise ValueError('expected score-partwise')
    names = {x.attrib['id']: x.findtext('part-name', '') for x in root.findall('./part-list/score-part')}
    parts = []
    for part in root.findall('part'):
        divisions = Fraction(1); events = []; measures = []
        for index, measure in enumerate(part.findall('measure')):
            cursor = Fraction(0); last_onset = Fraction(0); end = Fraction(0)
            for item in measure:
                if item.tag == 'attributes' and item.find('divisions') is not None:
                    divisions = Fraction(item.findtext('divisions'))
                    if divisions <= 0: raise ValueError('nonpositive divisions')
                elif item.tag in ('backup', 'forward'):
                    cursor += Fraction(item.findtext('duration', '0')) / divisions * (-1 if item.tag == 'backup' else 1)
                    if cursor < 0: raise ValueError('negative voice cursor')
                elif item.tag == 'note':
                    if item.find('grace') is not None: continue
                    duration = Fraction(item.findtext('duration', '0')) / divisions
                    if duration <= 0: raise ValueError('nonpositive timed note duration')
                    onset = last_onset if item.find('chord') is not None else cursor
                    pitch = item.find('pitch')
                    if pitch is None and item.find('rest') is None: raise ValueError('unsupported unpitched note')
                    spelling = None if item.find('rest') is not None else (
                        [pitch.findtext('step'), str(Fraction(pitch.findtext('alter', '0'))), int(pitch.findtext('octave'))]
                        if pitch is not None else None)
                    events.append({'measure': index, 'onset': str(onset), 'duration': str(duration),
                                   'pitch': spelling, 'voice': item.findtext('voice', '1'),
                                   'staff': item.findtext('staff', '1')})
                    last_onset = onset; end = max(end, onset + duration)
                    if item.find('chord') is None: cursor += duration
            measures.append(str(end))
        parts.append({'name': names.get(part.attrib['id'], ''), 'events': events, 'measureDurations': measures})
    if not parts: raise ValueError('score has no parts')
    return {'parts': parts, 'lyrics': len(root.findall('.//lyric')), 'noteheads': len(root.findall('.//notehead'))}

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'): self.urls.append(attrs['href'])
        if tag == 'img':
            self.urls.extend(attrs[k] for k in ('src', 'data-src') if attrs.get(k))

def original_image_url(html, page_url):
    parser = Links(); parser.feed(html)
    images = sorted({urljoin(page_url, u) for u in parser.urls
                     if '/wp-content/uploads/songs/' in u and re.search(r'\.(jpe?g|png)(?:\?|$)', u, re.I)
                     and not re.search(r'-\d+x\d+\.', u)})
    images = [u for u in images if urlparse(u).hostname == 'sh1991.sacredharpbremen.org']
    if len(images) != 1: raise ValueError(f'expected one original tune image, found {len(images)}')
    return images[0]

def acquire(work, url, suffix):
    """URL-addressed cache; verify reused bytes; never silently refresh a source."""
    path = work / 'inputs' / (digest(url.encode()) + suffix)
    receipt = path.with_suffix(path.suffix + '.receipt.json')
    if path.exists():
        meta = load(receipt)
        if meta['sha256'] != digest(path.read_bytes()) or meta['url'] != url: raise ValueError('cached source drift')
        return path, meta
    request = Request(url, headers={'User-Agent': 'ShapeNoteAtlas-local-research/1.0'})
    with urlopen(request, timeout=25) as response:
        data = response.read(10_000_001)
        if len(data) > 10_000_000: raise ValueError('source exceeds 10 MB bound')
        meta = {'url': url, 'finalUrl': response.url, 'httpStatus': response.status,
                'contentType': response.headers.get('Content-Type', ''), 'bytes': len(data),
                'sha256': digest(data), 'acquiredAt': now()}
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); write(receipt, meta)
    return path, meta

def candidate_pool(corpus):
    rows = []
    for song in corpus['songs']:
        coverage = song.get('sourceCoverageByBook', {}).get('sh1991', {})
        if not song.get('scoreByBook', {}).get('sh1991'): continue
        path = ROOT / coverage['manifestRawPath']
        if not path.is_file(): raise ValueError(f'missing retained XML: {path}')
        if digest(path.read_bytes()) != coverage['manifestSourceSha256']: raise ValueError('retained XML hash drift')
        parsed = score(path.read_bytes()); title = song.get('titlesByBook', {}).get('sh1991', song['title'])
        # Exact duplicate title or printed page is conservatively one group.
        # Transposition-invariant pitched interval/rhythm sequences join near-duplicate music too.
        fingerprints = []
        for part in parsed['parts']:
            sequence = []; first = None
            for event in part['events']:
                pitch = event['pitch']
                midi = None
                if pitch and len(pitch) == 3:
                    midi = 12 * (pitch[2] + 1) + {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[pitch[0]] + Fraction(pitch[1])
                    if first is None: first = midi
                sequence.append([str(midi - first) if midi is not None else None, event['duration']])
            fingerprints.append(sequence)
        rows.append({'songId': song['id'], 'songNo': song['songNo'], 'title': title,
                     'page': int(re.match(r'\d+', song['songNo']).group()), 'existingUrl': coverage['manifestSourceUrl'],
                     'existingSha256': coverage['manifestSourceSha256'],
                     'titleGroup': re.sub(r'[^a-z0-9]', '', title.lower()),
                     'musicGroup': digest(json.dumps(fingerprints).encode()), 'parts': len(parsed['parts'])})
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i: parents[i] = parents[parents[i]]; i = parents[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for key in (('page', row['page']), ('title', row['titleGroup']), ('music', row['musicGroup'])):
            if key in seen: parents[find(i)] = find(seen[key])
            seen[key] = i
    groups = {}
    for i, row in enumerate(rows): groups.setdefault(find(i), []).append(row['songId'])
    for i, row in enumerate(rows): row['group'] = digest('|'.join(sorted(groups[find(i)])).encode())[:20]
    return rows

def prepare(work):
    manifest = work / 'dataset.json'
    if manifest.exists():
        print('Dataset already frozen:', manifest); return
    corpus = load(ROOT / 'public/corpus.json'); pool = candidate_pool(corpus)
    selected = []; used = set()
    for bucket in range(5):
        candidates = [r for r in pool if min(r['page'] // 100, 4) == bucket]
        candidates.sort(key=lambda r: (0 if r['songNo'] in ('26', '115') else 1, digest((SEED + r['songId']).encode())))
        batch = []
        for row in candidates:
            if row['group'] in used: continue
            batch.append(row); used.add(row['group'])
            if len(batch) == 8: break
        if len(batch) != 8: raise ValueError('insufficient unique groups in stratum')
        selected.extend(batch)
    order = sorted(selected, key=lambda r: digest((SEED + 'split' + r['group']).encode()))
    for i, row in enumerate(order): row['split'] = 'train' if i < 24 else 'validation' if i < 32 else 'test'
    write(work / 'selection.json', {'seed': SEED, 'corpusSha256': digest((ROOT / 'public/corpus.json').read_bytes()), 'records': selected})
    catalogue, _ = acquire(work, 'https://shapenote.net/music.htm', '.html')
    links = Links(); links.feed(catalogue.read_text(errors='replace'))
    catalogue_urls = {urljoin('https://shapenote.net/music.htm', u) for u in links.urls}
    def pair(row):
        try:
            existing = row['existingUrl']; replacement = re.sub(r'(\d+[tb]?)d\.mxl$', r'\1a.mxl', existing)
            if replacement not in catalogue_urls: raise ValueError('as-written XML absent from live catalogue')
            label_path, label_meta = acquire(work, replacement, '.mxl'); parsed = score(label_path.read_bytes())
            page_url = f"https://sh1991.sacredharpbremen.org/{row['songNo']}"
            page, page_meta = acquire(work, page_url, '.html')
            image_url = original_image_url(page.read_text(errors='replace'), page_meta['finalUrl'])
            image_path, image_meta = acquire(work, image_url, Path(urlparse(image_url).path).suffix.lower())
            from PIL import Image
            with Image.open(image_path) as image: width, height = image.size; image.verify()
            return {**row, 'edition': 'sh1991', 'shapeSystem': 'four-shape', 'scanStyle': 'Bremen original printed edition',
                    'sourcePage': page_meta, 'image': {**image_meta, 'path': str(image_path.relative_to(ROOT)), 'width': width, 'height': height},
                    'label': {**label_meta, 'path': str(label_path.relative_to(ROOT)), 'variant': 'as-written' if replacement != existing else 'single-catalogue-version',
                              'parts': len(parsed['parts']), 'events': sum(len(p['events']) for p in parsed['parts']),
                              'lyricsAvailable': bool(parsed['lyrics']), 'literalNoteheadsAvailable': bool(parsed['noteheads'])},
                    'pairingStatus': 'candidate-needs-independent-event-review', 'trainingEligible': False,
                    'humanCorrectionMinutes': None, 'rights': {'sourcePublication': 'external-link-only', 'redistributeSource': False,
                    'uploadSource': False, 'trainingPermission': 'not-established', 'use': 'local source comparison and exploratory benchmark only'}}
        except Exception as error: return {**row, 'pairingStatus': 'acquisition-blocked', 'error': str(error)}
    with ThreadPoolExecutor(max_workers=3) as executor:
        records = []
        for row in executor.map(pair, selected):
            records.append(row); print(row['songNo'], row['pairingStatus'], flush=True)
    hashes = [r['image']['sha256'] for r in records if 'image' in r]
    if len(hashes) != len(set(hashes)): raise ValueError('duplicate source bytes across selected groups; resplit before any model run')
    dataset = {'schemaVersion': 1, 'seed': SEED, 'frozenAt': now(), 'sourceCorpusSha256': digest((ROOT / 'public/corpus.json').read_bytes()),
               'metricScope': 'exploratory pitch/rhythm only; candidate references, not certified ground truth',
               'splits': {'train': 24, 'validation': 8, 'test': 8}, 'records': records,
               'coverageLimits': 'SH1991 only, four-shape only, one scan family; no broad cross-book generalization',
               'trainingRunAuthorizedByManifest': False, 'safeToPromote': False}
    write(manifest, dataset)
    print(json.dumps({'selected': len(records), 'acquired': len(hashes), 'blocked': len(records) - len(hashes)}))

def align(reference, observed):
    """Minimum edit alignment of pitch/rest and duration; no same-length truncation."""
    symbol = lambda e: (tuple(e['pitch']) if e['pitch'] else None, e['duration'])
    a = [symbol(e) for e in reference]; b = [symbol(e) for e in observed]
    costs = [list(range(len(b) + 1))]
    for i in range(1, len(a) + 1):
        row = [i]
        for j in range(1, len(b) + 1): row.append(min(costs[i-1][j-1] + (a[i-1] != b[j-1]), costs[i-1][j] + 1, row[j-1] + 1))
        costs.append(row)
    i, j = len(a), len(b); pairs = []
    while i or j:
        if i and j and costs[i][j] == costs[i-1][j-1] + (a[i-1] != b[j-1]): pairs.append((i-1, j-1)); i -= 1; j -= 1
        elif i and costs[i][j] == costs[i-1][j] + 1: pairs.append((i-1, None)); i -= 1
        else: pairs.append((None, j-1)); j -= 1
    return list(reversed(pairs))

def compare(reference, observed):
    counts = Counter(referenceEvents=sum(len(p['events']) for p in reference['parts']), observedEvents=sum(len(p['events']) for p in observed['parts']))
    counts['referencePitched'] = sum(e['pitch'] is not None for p in reference['parts'] for e in p['events'])
    counts['observedPitched'] = sum(e['pitch'] is not None for p in observed['parts'] for e in p['events'])
    for i in range(max(len(reference['parts']), len(observed['parts']))):
        a = reference['parts'][i]['events'] if i < len(reference['parts']) else []
        b = observed['parts'][i]['events'] if i < len(observed['parts']) else []
        for x, y in align(a, b):
            if x is None: counts['insertions'] += 1; continue
            if y is None: counts['deletions'] += 1; continue
            left, right = a[x], b[y]
            counts['pitchMatches'] += left['pitch'] is not None and left['pitch'] == right['pitch']
            counts['durationMatches'] += left['duration'] == right['duration']
            counts['onsetMatches'] += (left['measure'], left['onset']) == (right['measure'], right['onset'])
    return {'counts': dict(counts), 'partCountMatch': len(reference['parts']) == len(observed['parts']),
            'measureCountsMatch': [len(p['measureDurations']) for p in reference['parts']] == [len(p['measureDurations']) for p in observed['parts']],
            'exactWrittenEvents': [[{k:e[k] for k in ('pitch','duration','measure','onset')} for e in p['events']] for p in reference['parts']] == [[{k:e[k] for k in ('pitch','duration','measure','onset')} for e in p['events']] for p in observed['parts']]}

def working_image(work, row, arm):
    source = ROOT / row['image']['path']
    if digest(source.read_bytes()) != row['image']['sha256']: raise ValueError('original scan drift')
    if arm == 'raw': return source
    if arm != 'grayscale-2x': raise ValueError('unknown preprocessing arm')
    from PIL import Image, __version__ as pillow_version
    destination = work / 'working' / arm / (row['songNo'] + '.png')
    receipt = destination.with_suffix('.receipt.json')
    if destination.exists():
        prior = load(receipt)
        if prior['sourceSha256'] != row['image']['sha256'] or prior['sha256'] != digest(destination.read_bytes()):
            raise ValueError('derived input drift')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        gray = image.convert('L')
        gray.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS).save(destination)
    write(receipt, {'sourceSha256': row['image']['sha256'], 'sha256': digest(destination.read_bytes()),
                    'method': 'Pillow grayscale L + 2x Lanczos; full frame; no threshold, erasure, or symbol reconstruction',
                    'pillowVersion': pillow_version, 'originalUnchanged': True})
    return destination


def validate_dataset(dataset):
    """Prevent duplicate IDs and known group leakage, including derived parts."""
    seen = set(); groups = {}
    for row in dataset['records']:
        if row['songNo'] in seen: raise ValueError('duplicate record ID')
        seen.add(row['songNo'])
        if row['split'] not in ('train', 'validation', 'test'): raise ValueError('unknown split')
        if row['group'] in groups and groups[row['group']] != row['split']: raise ValueError('group split leakage')
        groups[row['group']] = row['split']
        for field in ('image', 'label'):
            path = ROOT / row[field]['path']
            if digest(path.read_bytes()) != row[field]['sha256']: raise ValueError(f'{field} hash changed')


def engine_identity(executable):
    libraries = executable.parent.parent / 'lib'
    jars = {p.name: digest(p.read_bytes()) for p in sorted(libraries.glob('*.jar'))}
    return {'launcherSha256': digest(executable.read_bytes()),
            'librarySetSha256': digest(json.dumps(jars, sort_keys=True).encode()) if jars else None,
            'libraryCount': len(jars)}


def verify(work, arm='raw'):
    dataset = load(work / 'dataset.json'); validate_dataset(dataset)
    result = load(work / (('baseline' if arm == 'raw' else arm) + '-results.json'))
    if result['datasetSha256'] != digest((work / 'dataset.json').read_bytes()): raise ValueError('dataset changed')
    rows = {r['songNo']: r for r in dataset['records']}
    for receipt in result['records']:
        row = rows[receipt['songNo']]
        source = working_image(work, row, arm)
        if digest(source.read_bytes()) != receipt['inputSha256']: raise ValueError('input changed')
        if receipt.get('output'):
            output = ROOT / receipt['output']
            if digest(output.read_bytes()) != receipt['outputSha256']: raise ValueError('output changed')
            if receipt.get('metrics') != compare(score((ROOT / row['label']['path']).read_bytes()), score(output.read_bytes())):
                raise ValueError('scoring receipt differs from current evaluator')
    print('Verified source/label/input/output hashes and rescored', len(result['records']), 'receipts')


def scale_design(work):
    path = work / 'preprocessing-design.json'
    dataset_hash = digest((work / 'dataset.json').read_bytes())
    if path.exists():
        if load(path)['datasetSha256'] != dataset_hash: raise ValueError('scale design dataset drift')
        print('Scale design already frozen'); return
    ids = ['26', '83t', '68b', '72b', '89']
    dataset = load(work / 'dataset.json')
    if {r['songNo'] for r in dataset['records'] if r['split'] == 'train'} & set(ids) != set(ids):
        raise ValueError('fixed probe must remain entirely in training split')
    write(path, {'datasetSha256': dataset_hash, 'frozenAt': now(), 'trainingProbe': ids,
                 'candidateArm': 'grayscale-2x', 'selectionRule': {'pitchRecallGainAtLeast': .02,
                 'durationRecallRegressionAtMost': .01, 'noFewerExports': True},
                 'testPolicy': 'No held-out parameter tuning. Evaluate fixed transform only if training rule passes.',
                 'sourcePolicy': 'Immutable original; full-frame grayscale plus 2x Lanczos only.'})


def scale_decision(work):
    design = load(work / 'preprocessing-design.json'); ids = set(design['trainingProbe'])
    probe = load(work / 'grayscale-2x-results.json')
    if {r['songNo'] for r in probe['records']} != ids: raise ValueError('scale decision cohort differs from fixed training probe')
    dataset = load(work / 'dataset.json'); counts = Counter(); raw_rows = []
    for receipt in load(work / 'baseline-results.json')['records']:
        if receipt['songNo'] not in ids: continue
        raw_rows.append(receipt)
        if receipt.get('metrics'): counts.update(receipt['metrics']['counts'])
        else:
            row = next(r for r in dataset['records'] if r['songNo'] == receipt['songNo'])
            parsed = score((ROOT / row['label']['path']).read_bytes())
            counts['referenceEvents'] += sum(len(p['events']) for p in parsed['parts'])
            counts['referencePitched'] += sum(e['pitch'] is not None for p in parsed['parts'] for e in p['events'])
    if {r['songNo'] for r in raw_rows} != ids: raise ValueError('missing raw comparator')
    a = {'pitchRecall': counts['pitchMatches'] / counts['referencePitched'],
         'durationRecall': counts['durationMatches'] / counts['referenceEvents'],
         'exports': sum(r['status'] == 'exported' for r in raw_rows)}
    summary = probe['summary']['all']
    b = {'pitchRecall': summary['candidatePitchRecall'], 'durationRecall': summary['candidateDurationRecall'], 'exports': summary['exports']}
    rule = design['selectionRule']
    decision = {'cohort': sorted(ids), 'raw': a, 'grayscale2x': b,
                'passesPredeclaredTrainingRule': b['pitchRecall'] >= a['pitchRecall'] + rule['pitchRecallGainAtLeast'] and
                b['durationRecall'] >= a['durationRecall'] - rule['durationRecallRegressionAtMost'] and b['exports'] >= a['exports']}
    write(work / 'preprocessing-probe-decision.json', decision); print(json.dumps(decision))


def run(work, executable, jobs, timeout, arm='raw', record_ids=None, engine_constants=None):
    work = work.resolve()
    dataset = load(work / 'dataset.json'); dataset_hash = digest((work / 'dataset.json').read_bytes())
    if any(r['pairingStatus'] != 'candidate-needs-independent-event-review' for r in dataset['records']):
        raise ValueError('finish acquisition or freeze a new explicitly bounded cohort before running')
    validate_dataset(dataset)
    if arm == 'grayscale-2x':
        design = load(work / 'preprocessing-design.json')
        if design['datasetSha256'] != dataset_hash: raise ValueError('scale design dataset drift')
        record_ids = record_ids or design['trainingProbe']
        if set(record_ids) != set(design['trainingProbe']): raise ValueError('scale run limited to frozen training probe; create a separate protocol for held-out evaluation')
    if jobs < 1 or timeout <= 0: raise ValueError('jobs and timeout must be positive')
    if record_ids and set(record_ids) - {r['songNo'] for r in dataset['records']}: raise ValueError('unknown requested record')
    executable = executable.resolve(); identity = engine_identity(executable); results = []
    cohort = [r for r in dataset['records'] if not record_ids or r['songNo'] in record_ids]
    if not cohort: raise ValueError('empty requested cohort')
    output_name = 'baseline' if arm == 'raw' else arm
    existing_report = work / (output_name + '-results.json')
    if existing_report.exists() and {r['songNo'] for r in load(existing_report)['records']} != {r['songNo'] for r in cohort}:
        raise ValueError('refusing to overwrite a frozen result with a different cohort; use a separate work directory')
    def recognize(row):
        directory = work / output_name / row['songNo']; directory.mkdir(exist_ok=True, parents=True)
        receipt = directory / 'run.json'; source = working_image(work, row, arm); target = ROOT / row['label']['path']
        if digest(target.read_bytes()) != row['label']['sha256']: raise ValueError('label hash changed')
        command = [str(executable), '-batch', '-export']
        for constant in engine_constants or []:
            command.extend(['-constant', constant])
        command.extend(['-output', str(directory.resolve()), str(source.resolve())])
        if receipt.exists():
            prior = load(receipt)
            if prior['datasetSha256'] != dataset_hash: raise ValueError('stale run receipt')
            if prior['inputSha256'] != digest(source.read_bytes()) or prior['labelSha256'] != row['label']['sha256']: raise ValueError('cached input drift')
            if prior.get('engineIdentity') and prior['engineIdentity'] != identity: raise ValueError('cached engine drift')
            if prior['command'] != command: raise ValueError('cached command changed; use a new experiment directory')
            if prior.get('output') and prior['outputSha256'] != digest((ROOT / prior['output']).read_bytes()): raise ValueError('cached output drift')
            return prior
        started = time.monotonic(); timed_out = False
        with (directory / 'audiveris.log').open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try: code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True; os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
                code = 124
        exports = sorted(directory.rglob('*.mxl')) + sorted(directory.rglob('*.musicxml'))
        result = {'songNo': row['songNo'], 'split': row['split'], 'datasetSha256': dataset_hash, 'command': command,
                  'arm': arm, 'engineIdentity': identity, 'inputSha256': digest(source.read_bytes()), 'originalSha256': row['image']['sha256'], 'labelSha256': row['label']['sha256'],
                  'exitCode': code, 'timedOut': timed_out, 'seconds': time.monotonic() - started,
                  'sourceCertified': False, 'metricsStatus': 'candidate-reference-only', 'humanCorrectionMinutes': None,
                  'unsupportedMetrics': ['literal notehead/fill', 'lyric alignment', 'source-certified voice/staff', 'ties/slurs/repeats fidelity']}
        if len(exports) == 1:
            try:
                output = exports[0]; result['output'] = str(output.relative_to(ROOT)); result['outputSha256'] = digest(output.read_bytes())
                result['metrics'] = compare(score(target.read_bytes()), score(output.read_bytes())); result['status'] = 'exported'
            except Exception as error: result.update(status='invalid-export', error=str(error))
        else: result.update(status='no-export' if not exports else 'ambiguous-exports')
        write(receipt, result); return result
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for result in executor.map(recognize, cohort):
            results.append(result); print(result['songNo'], result['status'], round(result['seconds'], 2), flush=True)
            write(work / (output_name + '-progress.json'), {'completed': len(results), 'total': len(cohort), 'results': results})
    summary = {}
    for split in ('train', 'validation', 'test', 'all'):
        records = [r for r in results if split == 'all' or r['split'] == split]; counts = Counter()
        # Failed pages remain in denominators: zero credited matches, full reference mass.
        for result in records:
            if result.get('metrics'): counts.update(result['metrics']['counts'])
            else:
                row = next(x for x in dataset['records'] if x['songNo'] == result['songNo']); parsed = score((ROOT / row['label']['path']).read_bytes())
                counts['referenceEvents'] += sum(len(p['events']) for p in parsed['parts'])
                counts['referencePitched'] += sum(e['pitch'] is not None for p in parsed['parts'] for e in p['events'])
        summary[split] = {'pages': len(records), 'exports': sum(r['status'] == 'exported' for r in records), 'counts': dict(counts),
                          'candidatePitchRecall': counts['pitchMatches'] / counts['referencePitched'] if counts['referencePitched'] else None,
                          'candidatePitchPrecision': counts['pitchMatches'] / counts['observedPitched'] if counts['observedPitched'] else None,
                          'candidateDurationRecall': counts['durationMatches'] / counts['referenceEvents'] if counts['referenceEvents'] else None,
                          'candidateOnsetRecall': counts['onsetMatches'] / counts['referenceEvents'] if counts['referenceEvents'] else None}
    write(work / (output_name + '-results.json'), {'completedAt': now(), 'datasetSha256': dataset_hash, 'engine': str(executable), 'engineIdentityAtReport': identity,
          'legacyReceiptsWithoutEngineFingerprint': sum('engineIdentity' not in r for r in results),
          'summary': summary, 'records': results, 'modelFineTuned': False, 'trainingEligiblePages': 0,
          'interpretation': 'Exploratory baseline against unreviewed candidate labels, not certified accuracy or human correction time.'})
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--work', type=Path, default=DEFAULT_WORK)
    sub = parser.add_subparsers(dest='command', required=True); sub.add_parser('prepare')
    sub.add_parser('prepare-scale-probe'); sub.add_parser('summarize-scale-probe')
    runner = sub.add_parser('baseline'); runner.add_argument('--audiveris', type=Path, required=True); runner.add_argument('--jobs', type=int, default=2); runner.add_argument('--timeout', type=int, default=120); runner.add_argument('--arm', choices=['raw','grayscale-2x'], default='raw'); runner.add_argument('--record', action='append')
    runner.add_argument('--constant', action='append', help='Audiveris application constant key=value; part of the immutable command receipt')
    checker = sub.add_parser('verify'); checker.add_argument('--arm', choices=['raw', 'grayscale-2x'], default='raw')
    args = parser.parse_args(); args.work = args.work.resolve(); args.work.mkdir(parents=True, exist_ok=True)
    if args.command == 'prepare': prepare(args.work)
    elif args.command == 'prepare-scale-probe': scale_design(args.work)
    elif args.command == 'summarize-scale-probe': scale_decision(args.work)
    elif args.command == 'verify': verify(args.work, args.arm)
    else: run(args.work, args.audiveris, args.jobs, args.timeout, args.arm, args.record, args.constant)
