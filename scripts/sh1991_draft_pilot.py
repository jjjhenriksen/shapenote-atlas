#!/usr/bin/env python3
"""Frozen V7, local-only draft pilot on the entire original validation cohort."""
import argparse
import csv
from fractions import Fraction
import os
from pathlib import Path

import sh1991_pilot as pilot
import sh1991_fa_support as v7
from sh1991_barline_run import immutable
from sh1991_fa_survival import read_xml

WORK = pilot.DEFAULT_WORK / 'draft-pilot-v7-20261016'
EXECUTABLE = v7.ENGINE / 'app/build/install/app/bin/Audiveris'


def prepare():
    parent = pilot.load(pilot.DEFAULT_WORK / 'dataset.json')
    rows = [r for r in parent['records'] if r['split'] == 'validation']
    if len(rows) != 8:
        raise ValueError('Require the entire original eight-image validation cohort')
    pilot.validate_dataset(parent)
    engine = pilot.load(v7.WORK / 'engine.json')
    if pilot.engine_identity(EXECUTABLE) != engine['identity']:
        raise ValueError('Frozen V7 engine drift')
    lock = pilot.load(pilot.DEFAULT_WORK / 'heldout-v7/selection-lock.json')
    if lock['engine'] != engine:
        raise ValueError('Engine differs from final test selection')
    protocol = {
        'study': 'local-draft-pilot-v7-20261016', 'frozenAt': pilot.now(),
        'authorization': 'Jacqueline requested the proposed controlled draft-generation pilot, 2026-10-16',
        'selection': 'All eight original validation images, no outcome-based selection',
        'songs': [r['songNo'] for r in rows], 'engine': engine,
        'settings': {a: {'JAVA_OPTS': v7.settings(a)[0], 'constants': v7.settings(a)[1]}
                     for a in ('reference', 'candidate')},
        'parentDatasetSha256': pilot.digest((pilot.DEFAULT_WORK / 'dataset.json').read_bytes()),
        'priorSelectionLockSha256': pilot.digest((pilot.DEFAULT_WORK / 'heldout-v7/selection-lock.json').read_bytes()),
        'reviewSelection': 'Top staff in first system of each page; first printed measure, including pickup if present. Source-first pitch/duration review; no engine changes.',
        'priorExposure': 'Original baseline/voice studies exposed this validation cohort. New V7 application, not pristine held-out evidence.',
        'noTuning': True, 'sourceCertified': False, 'safeToPromote': False,
        'humanCorrectionMinutes': None,
        'limits': ['SH1991 only; one print/scan family, not cross-book validation.',
                   'Candidate XML disagreement is a review queue, not a verified correction count.',
                   'Agent source spot-review is not independent human acceptance or measured human correction time.'],
    }
    if (WORK / 'protocol.json').exists():
        old = pilot.load(WORK / 'protocol.json'); protocol['frozenAt'] = old['frozenAt']
    immutable(WORK / 'protocol.json', protocol)
    for arm in ('reference', 'candidate'):
        immutable(WORK / arm / 'dataset.json', {**parent, 'records': rows,
                  'splits': {'train': 0, 'validation': 8, 'test': 0}, 'experiment': protocol['study']})
    # Source-only cards use the pre-existing baseline layout, before V7 inference.
    from PIL import Image
    cards = []
    for row in rows:
        graph, = (pilot.DEFAULT_WORK / 'baseline' / row['songNo']).glob('*.omr')
        sheet = read_xml(graph, 'sheet#1/sheet#1.xml')
        staff = sheet.find('./page/system/part/staff')
        pts = [p.attrib for p in staff.findall('lines/line/point')]
        image = Image.open(pilot.ROOT / row['image']['path'])
        box = [0, max(0, int(min(float(p['y']) for p in pts))-65), image.width,
               min(image.height, int(max(float(p['y']) for p in pts))+65)]
        path = WORK / 'review' / (row['songNo'] + '-top-staff.png')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): image.crop(box).save(path)
        cards.append({'songNo': row['songNo'], 'sourceSha256': row['image']['sha256'],
                      'cropBox': box, 'card': str(path.relative_to(pilot.ROOT)),
                      'cardSha256': pilot.digest(path.read_bytes()), 'staffId': staff.get('id'),
                      'layoutSha256': pilot.digest(graph.read_bytes())})
    immutable(WORK / 'review-selection.json', {'protocolSha256': pilot.digest((WORK/'protocol.json').read_bytes()), 'cards': cards})
    return protocol


def run(arm):
    protocol = prepare(); directory = WORK / arm
    frozen_runner = WORK / 'recognition-runner.py'
    if not frozen_runner.exists(): frozen_runner.write_bytes(Path(__file__).read_bytes())
    if frozen_runner.read_bytes() != Path(__file__).read_bytes():
        raise ValueError('Runner changed after recognition; use analysis-only report/review, not new inference')
    home = str(pilot.DEFAULT_WORK / 'toolchain/jdk25/jdk-25.0.4.1+1/Contents/Home')
    settings = protocol['settings'][arm]
    immutable(directory / 'execution.json', {'JAVA_HOME': home, **settings,
              'protocolSha256': pilot.digest((WORK/'protocol.json').read_bytes()),
              'runnerSha256': pilot.digest(Path(__file__).read_bytes())})
    os.environ['JAVA_HOME'] = home; os.environ['JAVA_OPTS'] = settings['JAVA_OPTS']
    pilot.run(directory, EXECUTABLE, 2, 180, engine_constants=settings['constants'])


def report():
    protocol = prepare(); results = {}
    for arm in ('reference', 'candidate'):
        pilot.verify(WORK / arm)
        results[arm] = pilot.load(WORK / arm / 'baseline-results.json')
        execution = pilot.load(WORK / arm / 'execution.json')
        if any(execution[k] != v for k, v in protocol['settings'][arm].items()):
            raise ValueError('Frozen execution settings drift')
        if execution['protocolSha256'] != pilot.digest((WORK/'protocol.json').read_bytes()):
            raise ValueError('Execution protocol drift')
        if execution['runnerSha256'] != pilot.digest((WORK/'recognition-runner.py').read_bytes()):
            raise ValueError('Historical recognition runner drift')
        for row in results[arm]['records']:
            if row['engineIdentity'] != protocol['engine']['identity']:
                raise ValueError('Engine receipt drift')
            for constant in protocol['settings'][arm]['constants']:
                if constant not in row['command']:
                    raise ValueError('Frozen command constants missing')
    queue = []; pages = []; evidence = {}
    data = pilot.load(WORK / 'candidate/dataset.json')
    for row in data['records']:
        receipt = next(r for r in results['candidate']['records'] if r['songNo'] == row['songNo'])
        page = {'songNo': row['songNo'], 'title': row['title'], 'status': receipt['status'],
                'seconds': receipt['seconds'], 'output': receipt.get('output'),
                'referenceEvents': row['label']['events'], 'parts': row['parts']}
        if receipt.get('output'):
            ref = pilot.score((pilot.ROOT / row['label']['path']).read_bytes())
            obs = pilot.score((pilot.ROOT / receipt['output']).read_bytes())
            page['metrics'] = receipt['metrics']
            for part in range(max(len(ref['parts']), len(obs['parts']))):
                a = ref['parts'][part]['events'] if part < len(ref['parts']) else []
                b = obs['parts'][part]['events'] if part < len(obs['parts']) else []
                for i, j in pilot.align(a, b):
                    left = a[i] if i is not None else None; right = b[j] if j is not None else None
                    fields = ['missing-draft-event'] if right is None else ['extra-draft-event'] if left is None else [
                        k for k in ('pitch', 'duration', 'measure', 'onset') if left[k] != right[k]]
                    if fields:
                        queue.append({'songNo': row['songNo'], 'part': part+1,
                                      'referenceEvent': i+1 if i is not None else None,
                                      'draftEvent': j+1 if j is not None else None,
                                      'fields': fields, 'reference': left, 'draft': right,
                                      'status': 'needs-source-review-not-certified-error'})
            page['firstTwoTopStaffMeasures'] = [e for e in obs['parts'][0]['events'] if e['measure'] < 2]
            page['referenceFirstTwoTopStaffMeasures'] = [e for e in ref['parts'][0]['events'] if e['measure'] < 2]
            evidence[receipt['output']] = receipt['outputSha256']
        pages.append(page)
        for arm in ('reference', 'candidate'):
            for p in (WORK/arm/'baseline'/row['songNo']).glob('*'):
                if p.is_file(): evidence[str(p.relative_to(pilot.ROOT))] = pilot.digest(p.read_bytes())
    pilot.write(WORK / 'review-queue.json', {'certifiedErrors': None, 'humanCorrectionMinutes': None, 'records': queue})
    with (WORK/'review-queue.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['songNo','part','referenceEvent','draftEvent','fields','status'])
        for r in queue: w.writerow([r[k] if k != 'fields' else ';'.join(r[k]) for k in ('songNo','part','referenceEvent','draftEvent','fields','status')])
    pilot.write(WORK / 'report.json', {'protocol': protocol,
                'summary': {a: r['summary']['all'] for a, r in results.items()},
                'pages': pages, 'reviewQueueLocations': len(queue),
                'evidenceSha256': evidence, 'safeToPromote': False, 'sourceCertified': False,
                'recognitionRunnerSha256': pilot.digest((WORK/'recognition-runner.py').read_bytes()),
                'analysisRunnerSha256': pilot.digest(Path(__file__).read_bytes()),
                'humanCorrectionMinutes': None})
    print({a:r['summary']['all'] for a,r in results.items()})
    print('Review-queue locations:', len(queue))


def review():
    """Compare explicitly saved agent source observations, never tune recognition."""
    prepare()
    report = pilot.load(WORK / 'report.json')
    source = pilot.load(WORK / 'source-observations.json')
    if source['sourceCards'] != pilot.load(WORK/'review-selection.json')['cards']:
        raise ValueError('Source review selection drift')
    segments = []
    for page in report['pages']:
        for measure, observations in enumerate(source['expectedTopStaffMeasures'][page['songNo']]):
            expected = []; onset = Fraction(0)
            for pitch, duration in observations:
                if pitch == 'rest': spelling = None
                else:
                    alter = '1' if '#' in pitch else '-1' if 'b' in pitch else '0'
                    spelling = [pitch[0], alter, int(pitch[-1])]
                expected.append({'pitch': spelling, 'duration': duration,
                                 'onset': str(onset), 'measure': measure})
                onset += Fraction(duration)
            actual = [e for e in page['firstTwoTopStaffMeasures'] if e['measure'] == measure]
            reference = [e for e in page['referenceFirstTwoTopStaffMeasures'] if e['measure'] == measure]
            fields = ('pitch','duration','onset','measure')
            normalize = lambda events: [{k:e[k] for k in fields} for e in events]
            operations = []
            for i, j in pilot.align(expected, actual):
                if i is None: operations.append({'action':'remove-draft-event','draftIndex':j+1})
                elif j is None: operations.append({'action':'add-source-event','sourceIndex':i+1,'source':expected[i]})
                else:
                    edits = {k:expected[i][k] for k in fields if expected[i][k] != actual[j][k]}
                    if edits: operations.append({'action':'change-event-fields','draftIndex':j+1,'fields':edits})
            segments.append({'songNo':page['songNo'],'topStaffMeasureIndex':measure,
                             'selection':'predeclared' if measure == 0 else 'uniform-supplemental',
                             'sourceEvents':len(expected),'draftEvents':len(actual),
                             'pitchDurationOnsetExact':normalize(expected)==normalize(actual),
                             'sourceAgreesWithCandidateReference':normalize(expected)==normalize(reference),
                             'operations':operations})
    result = {'reviewer':source['reviewer'],'sourceObservationSha256':pilot.digest((WORK/'source-observations.json').read_bytes()),
              'sourceEvents':sum(r['sourceEvents'] for r in segments),
              'segmentsReviewed':len(segments),'segmentsNeedingCorrection':sum(not r['pitchDurationOnsetExact'] for r in segments),
              'suggestedEventEditActions':sum(len(r['operations']) for r in segments),
              'segments':segments,'humanCorrectionMinutes':None,'sourceCertified':False,
              'safeToPromote':False,
              'limits':'Agent visual spot-review, not independent human gold. Edit scripts are an event-level workload proxy, not measured editor actions/time; segmentation/voice fixes can span measures. No full-score acceptance.'}
    pilot.write(WORK/'source-review.json',result)
    print({k:v for k,v in result.items() if k!='segments'})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'reference', 'candidate', 'report', 'review'])
    a = p.parse_args()
    if a.action == 'prepare': prepare()
    elif a.action == 'report': report()
    elif a.action == 'review': review()
    else: run(a.action)
