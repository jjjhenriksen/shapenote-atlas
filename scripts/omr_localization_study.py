#!/usr/bin/env python3
"""New research training populations plus complete-window native localization.

Freeze model/engine/scope before viewing the fifth originally ranked SH2025
source (219). Freeze its complete source-head census before ONE recognition.
No previous 219 score/reference XML is used as truth. No score repair/admission.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import zipfile
from xml.etree import ElementTree as ET

import omr_followup_study as prior
import omr_localization_eval as localization
import omr_training_population as training
import sh1991_head_audit as native
import sh1991_pilot as pilot

ROOT, WORK = training.ROOT, training.WORK
OUT = WORK/'expanded-localization-v1'
archive = training.prior.archive
load = training.prior.prior.load


def protocol():
    import numpy
    from PIL import __version__ as pillow
    base = prior.protocol()
    eligible = load(training.prior.SELECTION)['eligible']
    if [r['songNo'] for r in eligible[:5]] != ['501t', '184', '188', '80t', '219']:
        raise ValueError('Original reserved rank drift')
    source = ROOT/'work/source-images/2025/219-he-hath-saved-us-4c1ffc8918.jpg'
    engine_file = WORK/'accuracy-tracks-v1/penn-test/protocol.json'
    engine = load(engine_file)
    if pilot.engine_identity(Path(engine['engineExecutable'])) != engine['engine']:
        raise ValueError('Prior fixed V7 engine drift')
    if archive.digest(engine['templatePointsPath']) != engine['templatePointsSha256']:
        raise ValueError('Fixed engine template-point drift')
    inputs = dict(base['inputsSha256'])
    paths = [Path(__file__), Path(training.__file__), Path(localization.__file__), Path(native.__file__), Path(pilot.__file__),
             source, engine_file, Path(engine['templatePointsPath']), Path(engine['JAVA_HOME'])/'bin/java']
    for song, labels, image in training.modern_inputs(): paths.extend((labels, image))
    for path in paths: inputs[str(path.relative_to(ROOT))] = archive.digest(path)
    return {'trainingRecipe': training.RECIPE, 'localizationRecipe': localization.RECIPE,
            'numpyVersion': numpy.__version__, 'pillowVersion': pillow,
            'selected': eligible[4], 'sourcePath': str(source.relative_to(ROOT)), 'sourceSha256': archive.digest(source),
            'selectionRule': 'Fifth original hash-ranked eligible source; first four consumed.',
            'scope': 'Opening system, first four written measure spans (including pickup if present; entire opening system if fewer). All pitched heads in four complete supplied staff windows, not a fixed positive-only sample.',
            'sourceExposure': 'Generic archived recognition/metadata may exist; no earlier 219 XML or graph opened as source truth in this run.',
            'labels': 'Provisional same-agent source reading, not independent source gold.',
            'engineExecutable': engine['engineExecutable'], 'engine': engine['engine'],
            'JAVA_HOME': engine['JAVA_HOME'], 'settings': engine['settings'],
            'recognitionPolicy': 'Exactly one unchanged-engine run after source census freezes; reuse completed receipt; preserve failure without retry/replacement.',
            'inputsSha256': inputs}


def check(out):
    current = protocol()
    if load(Path(out)/'development-protocol.json') != current:
        raise ValueError('Frozen code/input/engine drift; retain run and use a new protocol version')
    return current


def develop(out):
    out = Path(out); check(out)
    target = out/'development.json'
    if target.exists(): return load(target)
    rows = training.samples(); cohorts = {}
    legacy_cache = {}
    for group in sorted({r['group'] for r in rows}):
        testing = [r for r in rows if r['group'] == group]
        populations = training.RECIPE['populations'] if group.startswith('SH2025/') else ['legacy', 'expanded']
        predictions = {}
        for population in populations:
            fitting = training.population(rows, population, exclude=group)
            if {r['sourceSha256'] for r in fitting} & {r['sourceSha256'] for r in testing}:
                raise ValueError('Whole-source fold leakage')
            key = group if group.startswith('SH1991/') else 'all-legacy'
            if population == 'legacy' and key in legacy_cache:
                bank = legacy_cache[key]
            else:
                bank = training.fit(fitting)
                if population == 'legacy': legacy_cache[key] = bank
            predictions[population] = [{'id': r['id'], 'label': r['label'], **training.predict(r['pixels'], bank)} for r in testing]
        for index in range(len(testing)):
            baseline = predictions['legacy'][index]['prediction']
            for values in predictions.values(): values[index]['baseline'] = baseline
        cohorts[group] = {population: {'metrics': training.prior.classifier.metrics(values),
                                       'selective': training.prior.classifier.metrics([dict(r, prediction=r['selectivePrediction']) for r in values]),
                                       'predictions': values} for population, values in predictions.items()}
    modern = [value for name, value in cohorts.items() if name.startswith('SH2025/')]
    eligible = [p for p in training.RECIPE['populations'] if all(c[p]['metrics']['correct'] >= c['legacy']['metrics']['correct'] for c in modern)]
    selected = min(eligible, key=lambda p: (-sum(c[p]['metrics']['correct'] for c in modern), training.RECIPE['populations'].index(p)))
    report = {'protocolSha256': archive.digest(out/'development-protocol.json'),
              'phase': 'consumed development; whole-source-page folds, never random crop splits',
              'populationCounts': dict(Counter(r['group'] for r in rows)),
              'classCounts': {p: dict(Counter(r['label'] for r in training.population(rows, p))) for p in training.RECIPE['populations']},
              'cohorts': cohorts, 'eligibleSH2025Populations': eligible, 'selectedSH2025Population': selected,
              'SH1991Routing': 'retain unchanged legacy bank', 'safeToPromote': False}
    check(out); archive.immutable(target, archive.json_bytes(report)); return report


def freeze(out):
    out = Path(out); current = check(out); development = load(out/'development.json')
    if development['protocolSha256'] != archive.digest(out/'development-protocol.json'):
        raise ValueError('Development report protocol drift')
    result = {'developmentProtocolSha256': archive.digest(out/'development-protocol.json'),
              'developmentReportSha256': archive.digest(out/'development.json'),
              'selectedPopulation': development['selectedSH2025Population'],
              'sourceSha256': current['sourceSha256'], 'scope': current['scope'],
              'sourceEdition': 'SH2025 supplied by original catalogue selection', 'engine': current['engine']}
    archive.immutable(out/'transfer-protocol.json', archive.json_bytes(result)); return result


def observations(out, labels_path):
    out, labels_path = Path(out), Path(labels_path); current = check(out)
    if not (out/'transfer-protocol.json').exists():
        raise ValueError('Freeze population/engine/scope BEFORE source inspection')
    frozen = freeze(out); labels = load(labels_path)
    if labels['sourceSha256'] != current['sourceSha256'] or labels['completeHeadCensus'] is not True:
        raise ValueError('Need a source-bound complete-window census')
    windows = labels['windows']; rows = labels['rows']
    if len(windows) != 4 or [w['staff'] for w in windows] != list(range(4)):
        raise ValueError('Require four ordered complete staff windows')
    for index, window in enumerate(windows):
        a, b, c, d = window['box']
        if not all(math.isfinite(v) for v in (a, b, c, d)) or not 0 <= a < c or not 0 <= b < d:
            raise ValueError('Invalid complete window')
        if index and windows[index-1]['box'][3] > b:
            raise ValueError('Overlapping source staff windows')
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Require nonempty unique source heads')
    for row in rows:
        if type(row['staff']) is not int or row['staff'] not in range(4): raise ValueError('Unknown source staff')
        a, b, c, d = windows[row['staff']]['box']
        if not all(math.isfinite(row[k]) for k in ('x', 'y', 'interline')) or row['interline'] < 3:
            raise ValueError('Invalid observed center/interline')
        if not a <= row['x'] < c or not b <= row['y'] < d: raise ValueError('Source head outside frozen window')
        if row['label'] is not None and row['label'] not in training.prior.geometry.GLYPHS:
            raise ValueError('Unknown label must remain null, not an invented class')
    lock = {'transferProtocolSha256': archive.digest(out/'transfer-protocol.json'), 'labelsSha256': archive.digest(labels_path)}
    archive.immutable(out/'inference-lock.json', archive.json_bytes(lock))
    return current, frozen, labels, lock


def recognize(out, current):
    out = Path(out); receipt_path = out/'recognition.json'
    execution = {'inferenceLockSha256': archive.digest(out/'inference-lock.json'),
                 'engine': current['engine'], 'settings': current['settings'], 'sourceSha256': current['sourceSha256']}
    archive.immutable(out/'execution.json', archive.json_bytes(execution))
    if receipt_path.exists():
        result = load(receipt_path)
        if result['executionSha256'] != archive.digest(out/'execution.json'): raise ValueError('Recognition execution drift')
        for path, sha in result['artifactsSha256'].items():
            if archive.digest(ROOT/path) != sha: raise ValueError('Raw recognition artifact drift')
        return result
    if (out/'started.json').exists(): raise ValueError('Recognition already started; preserve log, never silently retry')
    raw = out/'raw'; raw.mkdir(parents=True, exist_ok=True)
    command = [current['engineExecutable'], '-batch', '-export']
    for constant in current['settings']['constants']: command += ['-constant', constant]
    command += ['-output', str(raw.resolve()), str((ROOT/current['sourcePath']).resolve())]
    archive.immutable(out/'started.json', archive.json_bytes({'command': command, 'executionSha256': archive.digest(out/'execution.json'), 'beganAt': pilot.now()}))
    environment = {**os.environ, 'JAVA_HOME': current['JAVA_HOME'], 'JAVA_OPTS': current['settings']['JAVA_OPTS']}
    started = time.monotonic(); timeout = False
    with (out/'audiveris.log').open('w') as log:
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=log, start_new_session=True)
        try: code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timeout = True; os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
            code = 124
    graphs = list(raw.rglob('*.omr')); exports = list(raw.rglob('*.mxl'))
    artifacts = [out/'audiveris.log', *graphs, *exports]
    result = {'executionSha256': archive.digest(out/'execution.json'), 'command': command,
              'exitCode': code, 'timedOut': timeout, 'seconds': time.monotonic()-started,
              'status': 'graph-ready' if code == 0 and len(graphs) == 1 else 'recognition-failed',
              'graph': str(graphs[0].relative_to(ROOT)) if len(graphs) == 1 else None,
              'artifactsSha256': {str(p.relative_to(ROOT)): archive.digest(p) for p in artifacts},
              'endedAt': pilot.now(), 'wholeScoresAccepted': 0}
    check(out); archive.immutable(receipt_path, archive.json_bytes(result)); return result


def graph_heads(graph_path, source_path, image_size):
    with zipfile.ZipFile(graph_path) as saved:
        book = ET.fromstring(saved.read('book.xml'))
        sheets = book.findall('sheet')
        if len(sheets) != 1 or sheets[0].findtext('input/number') != '1': raise ValueError('Only a single bound source image is supported')
        path = sheets[0].findtext('input/path')
        if not path or Path(path).resolve() != Path(source_path).resolve(): raise ValueError('Native source path requires registration')
        number = sheets[0].get('number')
        root = ET.fromstring(saved.read(f'sheet#{number}/sheet#{number}.xml'))
    picture = root.find('picture')
    if picture is None or (int(picture.get('width')), int(picture.get('height'))) != image_size:
        raise ValueError('Native coordinate dimensions require registration')
    rows = []
    for system in root.findall('./page/system'):
        if any(h.find('bounds') is None for h in system.iter('head')): raise ValueError('Native head lacks localization; denominator unavailable')
        for row in native.heads_in_graph(system):
            rows.append({**row, 'rawNativeId': row['id'], 'id': str(system.get('id'))+':'+row['id']})
    if len({r['id'] for r in rows}) != len(rows): raise ValueError('Duplicate native head IDs')
    return rows


def evaluate(out, labels_path):
    from PIL import Image
    out = Path(out); current, frozen, labels, lock = observations(out, labels_path)
    receipt = recognize(out, current)  # Exactly one run or receipt-only reuse.
    target = out/'report.json'
    if target.exists():
        report = load(target)
        if report['inferenceLockSha256'] != archive.digest(out/'inference-lock.json') or report['recognitionSha256'] != archive.digest(out/'recognition.json'):
            raise ValueError('Evaluation binding drift')
        return report
    rows = training.samples()
    if current['sourceSha256'] in {r['sourceSha256'] for r in rows}: raise ValueError('Reserved source entered training')
    populations = list(dict.fromkeys(['legacy', frozen['selectedPopulation']]))
    banks = {p: training.fit(training.population(rows, p)) for p in populations}
    targets = labels['rows']; output = {}
    with Image.open(ROOT/current['sourcePath']) as image:
        windows = [training.prior.geometry.checked_box(image, w['box']) for w in labels['windows']]
        lattices = [training.prior.geometry.staff_lines(image, box) for box in windows]
        conditional = {p: [] for p in populations}
        for row in targets:
            if row['label'] is None: continue
            crop = training.prior.classifier.crop(image, row['x'], row['y'], row['interline'])
            values = {p: training.predict(crop, b) for p, b in banks.items()}
            for p in populations: conditional[p].append({'id': row['id'], 'label': row['label'], 'baseline': values['legacy']['prediction'], **values[p]})
        heads = graph_heads(ROOT/receipt['graph'], ROOT/current['sourcePath'], image.size) if receipt['status'] == 'graph-ready' else None
        predictions = []
        if heads is not None:
            for head in heads:
                candidates = [i for i, (a, b, c, d) in enumerate(windows) if a <= head['x'] < c and b <= head['y'] < d]
                if not candidates: continue
                if len(candidates) != 1: raise ValueError('Ambiguous prediction window')
                staff = candidates[0]; row = dict(head, staff=staff, models={})
                for p, bank in banks.items():
                    value = {'prediction': None, 'selectivePrediction': None, 'reason': 'unresolved-auto-staff-lattice'}
                    if lattices[staff]['status'] == 'proposal':
                        try:
                            crop = training.prior.classifier.crop(image, head['x'], head['y'], lattices[staff]['interline'])
                            value = training.predict(crop, bank)
                        except ValueError: value['reason'] = 'automatic-crop-outside-source'
                    row['models'][p] = value
                predictions.append(row)
        for p in populations:
            automatic = [dict(r, **r['models'][p]) for r in predictions]
            sensitivity = {}
            if heads is not None:
                for radius in localization.RECIPE['sensitivityRadii']:
                    pairs = localization.match(targets, automatic, radius)
                    sensitivity[str(radius)] = {'summary': localization.summarize(targets, automatic, pairs), 'pairs': pairs}
            output[p] = {'sourceCentered': training.prior.classifier.metrics(conditional[p]),
                         'sourceCenteredPredictions': conditional[p],
                         'automatic': sensitivity or None,
                         'automaticSelective': localization.summarize(targets, automatic, sensitivity['0.5']['pairs'], 'selectivePrediction') if sensitivity else None}
    report = {'inferenceLockSha256': archive.digest(out/'inference-lock.json'), 'recognitionSha256': archive.digest(out/'recognition.json'),
              'selectedPopulation': frozen['selectedPopulation'], 'sourceHeadCount': len(targets),
              'sourceByClass': dict(Counter(r['label'] or 'unresolved' for r in targets)),
              'completeWindows': labels['windows'], 'automaticStaffLattices': lattices,
              'nativeHeadNodesAllImage': len(heads) if heads is not None else None,
              'nativeHeadsInWindows': len(predictions) if heads is not None else None,
              'inHeadChordInWindows': sum(r['inHeadChord'] for r in predictions) if heads is not None else None,
              'models': output, 'automaticPredictions': predictions,
              'recognitionStatus': receipt['status'], 'sourceCertified': False, 'safeToPromote': False,
              'wholeScoresAccepted': 0, 'pitchRhythmAccuracy': None,
              'limits': ['Complete but provisional same-agent census, supplied staff/windows; not independently certified gold.',
                         'Automatic centers are native graph nodes, not necessarily scheduled/exported notes.',
                         'Unmatched predictions are geometric mismatches/duplicates/possible extras, not automatically certified false positives.',
                         'Crop-target accuracy and automatic-center/all-source accuracy are distinct; no missing heads removed from denominator.',
                         'No pitch/rhythm, lyric or whole-score acceptance. Reserved 219 now consumed.']}
    check(out)
    if archive.digest(labels_path) != lock['labelsSha256']: raise ValueError('Source census drift during inference')
    archive.immutable(target, archive.json_bytes(report)); return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true'); mode.add_argument('--development', action='store_true')
    mode.add_argument('--freeze-transfer', action='store_true'); mode.add_argument('--labels', type=Path)
    args = parser.parse_args()
    if args.prepare:
        archive.immutable(args.out/'development-protocol.json', archive.json_bytes(protocol())); print('Frozen before reserved-source inspection.')
    elif args.development:
        r = develop(args.out)
        print(json.dumps({'selected': r['selectedSH2025Population'], 'eligible': r['eligibleSH2025Populations'],
                          'counts': r['populationCounts'], 'cohorts': {g: {p:v['metrics'] for p,v in c.items()} for g,c in r['cohorts'].items()}}, indent=2))
    elif args.freeze_transfer: print(json.dumps(freeze(args.out), indent=2))
    else:
        r = evaluate(args.out, args.labels)
        print(json.dumps({'sourceHeads': r['sourceHeadCount'], 'nativeHeadsInWindows': r['nativeHeadsInWindows'],
                          'selected': r['selectedPopulation'], 'models': {p:{'sourceCentered':v['sourceCentered'], 'automatic':v['automatic']['0.5']['summary'] if v['automatic'] else None} for p,v in r['models'].items()}}, indent=2))
