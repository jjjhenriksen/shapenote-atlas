#!/usr/bin/env python3
"""Replay frozen V3 into reusable source-point diagnostics; no recognition."""
import argparse
from collections import Counter
from fractions import Fraction
from pathlib import Path

import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
import sh1991_fa_survival as survival
from sh1991_head_audit import heads_in_graph, write_report
from omr_point_eval import summarize_points, negative_diagnostic, paired_proposals, threshold_check

DOCS = pilot.ROOT / 'docs/experiments'
PRIOR = DOCS / 'sh1991-fa-proximity-v3-20261015.json'
BENCHMARK = DOCS / 'sh1991-fa-discrimination-benchmark-20261015.json'
SELECTION = DOCS / 'sh1991-eval-review-selection-20261015.json'
REVIEW = DOCS / 'sh1991-eval-source-review-20261015.json'
WORK = pilot.DEFAULT_WORK / 'eval-diagnostics-v4'
ARMS = ('control', 'v2-control', 'candidate')


def checked_inputs():
    prior = pilot.load(PRIOR); benchmark = pilot.load(BENCHMARK)
    if pilot.digest(BENCHMARK.read_bytes()) != prior['benchmarkSha256']:
        raise ValueError('frozen benchmark drift')
    audit_path = DOCS / 'sh1991-head-shape-audit-20261015.json'
    if pilot.digest(audit_path.read_bytes()) != benchmark['parentAuditSha256']:
        raise ValueError('frozen source audit drift')
    evidence = {str(PRIOR.relative_to(pilot.ROOT)): pilot.digest(PRIOR.read_bytes()),
                str(BENCHMARK.relative_to(pilot.ROOT)): pilot.digest(BENCHMARK.read_bytes()),
                str(audit_path.relative_to(pilot.ROOT)): pilot.digest(audit_path.read_bytes()),
                **prior['evidenceSha256']}
    if set(benchmark['sourceImages']) != set(prior['protocol']['trainingProbe']):
        raise ValueError('unexpected benchmark cohort')
    for source in benchmark['sourceImages'].values():
        if source['split'] != 'train':
            raise ValueError('held-out source forbidden')
        evidence[source['path']] = source['sha256']
    verify_hashes(evidence)
    return prior, benchmark, pilot.load(audit_path), evidence


def verify_hashes(evidence):
    for path, sha in evidence.items():
        if pilot.digest((pilot.ROOT / path).read_bytes()) != sha:
            raise ValueError('frozen evidence drift: ' + path)


def prediction(native):
    if native is None:
        return None
    return {'nativeLabel': native['shape'], 'fill': fa.fill_of(native['shape']),
            'stages': {key: native[key] for key in survival.STAGES}}


def read_events(log):
    events = []
    for number, line in enumerate(log.read_text().splitlines(), 1):
        if not line.startswith('FAPROBE|'):
            continue
        columns = line.split('|')
        if len(columns) != 10 or any(columns[i] not in ('true', 'false') for i in (8, 9)):
            raise ValueError('malformed proposal')
        events.append({'pointId': columns[1], 'shape': columns[2], 'x': float(columns[3]),
            'y': float(columns[4]), 'distance': float(columns[5]), 'anchor': columns[7],
            'seed': columns[8] == 'true', 'veto': columns[9] == 'true', 'line': number})
    return events


def unmatched_queue(prior, audit):
    queue = []
    for arm in ARMS:
        used = {(row['sourceId'], row['retainedHead']['id']) for row in prior['arms'][arm]['benchmarkRows']
                if row.get('retainedHead')}
        used_by_song = {(row['songNo'], head_id) for source_id, head_id in used
                        for row in audit['observations'] if row['id'] == source_id}
        for song in sorted({p['songNo'] for p in audit['sourcePointers']}):
            directory = pilot.DEFAULT_WORK / 'fa-discrimination-v3' / arm / 'baseline' / song
            graphs = list(directory.glob('*.omr'))
            if len(graphs) != 1:
                raise ValueError('missing or ambiguous graph')
            sheet = survival.read_xml(graphs[0], 'sheet#1/sheet#1.xml')
            record = next(r for r in pilot.load(directory.parent.parent / 'baseline-results.json')['records'] if r['songNo'] == song)
            graph_rows, _ = survival.graph_rows(sheet, survival.read_xml(pilot.ROOT / record['output']))
            for window in [p for p in audit['sourcePointers'] if p['songNo'] == song]:
                for head in heads_in_graph(sheet):
                    if (head['staffId'] != window['staffId'] or not 270 <= head['x'] < 1030
                            or not window['cropBox'][1] <= head['y'] < window['cropBox'][3]
                            or (song, head['id']) in used_by_song):
                        continue
                    queue.append({'id': arm + '/' + song + '/' + head['id'], 'arm': arm, 'songNo': song,
                        'windowId': window['windowId'], 'headId': head['id'], 'x': head['x'], 'y': head['y'],
                        'nativeLabel': head['shape'], 'stages': {key: graph_rows[head['id']][key] for key in survival.STAGES},
                        'sourceLabel': 'unreviewed'})
    for arm in ARMS:
        if sum(r['arm'] == arm for r in queue) != prior['arms'][arm]['headAudit']['unmatchedGraphNodesInWindows']:
            raise ValueError('review queue does not reproduce frozen unmatched count')
    return sorted(queue, key=lambda r: (r['arm'], r['windowId'], r['x'], r['y'], r['id']))


def selection_for(queue, benchmark):
    selected = []
    windows = sorted({r['windowId'] for r in queue if r['arm'] == 'candidate'})
    for window in windows:
        candidates = [r for r in queue if r['arm'] == 'candidate' and r['windowId'] == window]
        # Two x-spread retained unmatched heads per occupied candidate window.
        indices = sorted({len(candidates) // 3, 2 * len(candidates) // 3})
        for index in indices:
            row = candidates[index]
            selected.append({k: row[k] for k in ('id', 'songNo', 'windowId', 'x', 'y')})
    return {'schemaVersion': 1, 'parentResultSha256': pilot.digest(PRIOR.read_bytes()),
            'selectionRule': 'Two x-spread candidate-arm retained unmatched heads per occupied audited window, indices floor(n/3), floor(2n/3), deduplicated. No shape, fill or future label used.',
            'scope': 'Training-only error-directed diagnostic, not an unbiased precision sample.',
            'sourceImages': {song: benchmark['sourceImages'][song] for song in sorted({r['songNo'] for r in selected})},
            'rows': selected}


def prepare_review():
    from PIL import Image, ImageDraw
    prior, benchmark, audit, evidence = checked_inputs()
    selection = selection_for(unmatched_queue(prior, audit), benchmark)
    if SELECTION.exists() and pilot.load(SELECTION) != selection:
        raise ValueError('refusing to replace frozen review selection')
    if not SELECTION.exists():
        write_report(SELECTION, selection)
    WORK.mkdir(parents=True, exist_ok=True)
    cards = []
    for row in selection['rows']:
        source = Image.open(pilot.ROOT / selection['sourceImages'][row['songNo']]['path']).convert('RGB')
        left, top = int(row['x']) - 50, int(row['y']) - 30
        crop = source.crop((left, top, left + 100, top + 60)).resize((400, 240))
        card = Image.new('RGB', (420, 280), 'white'); card.paste(crop, (10, 32))
        draw = ImageDraw.Draw(card); draw.text((8, 6), row['id'], fill='black')
        x = 10 + 4 * (row['x'] - left); y = 32 + 4 * (row['y'] - top)
        # Bracket the center; keep the source mark itself unobscured.
        for start, end in [((x-16, y), (x-8, y)), ((x+8, y), (x+16, y)),
                           ((x, y-16), (x, y-8)), ((x, y+8), (x, y+16))]:
            draw.line((start, end), fill='red', width=1)
        cards.append(card)
    contacts = []
    for start in range(0, len(cards), 12):
        contact = Image.new('RGB', (1260, 1120), '#dddddd')
        for index, card in enumerate(cards[start:start+12]):
            contact.paste(card, (index % 3 * 420, index // 3 * 280))
        path = WORK / f'source-review-{start//12+1}.png'; contact.save(path)
        contacts.append({'path': str(path.relative_to(pilot.ROOT)), 'sha256': pilot.digest(path.read_bytes())})
    pilot.write(WORK / 'contacts.json', contacts)
    verify_hashes(evidence)
    print('Prepared source-only review cards:', len(cards), contacts)


def source_review(selection):
    if not REVIEW.exists():
        raise ValueError('source review incomplete')
    review = pilot.load(REVIEW)
    if review['selectionSha256'] != pilot.digest(SELECTION.read_bytes()):
        raise ValueError('review selection drift')
    expected = {r['id'] for r in selection['rows']}
    if len(review['rows']) != len(expected) or {r['id'] for r in review['rows']} != expected:
        raise ValueError('review labels incomplete or duplicate')
    if any(r['label'] not in ('head', 'non_head', 'uncertain') for r in review['rows']):
        raise ValueError('invalid review label')
    for contact in review['sourceContacts']:
        if pilot.digest((pilot.ROOT / contact['path']).read_bytes()) != contact['sha256']:
            raise ValueError('source contact drift')
    return review


def summarize(output):
    prior, benchmark, audit, evidence = checked_inputs()
    sources = {r['id']: r for r in benchmark['rows']}
    queue = unmatched_queue(prior, audit)
    selection = selection_for(queue, benchmark)
    if pilot.load(SELECTION) != selection:
        raise ValueError('frozen selection drift')
    review = source_review(selection)
    evidence[str(SELECTION.relative_to(pilot.ROOT))] = pilot.digest(SELECTION.read_bytes())
    evidence[str(REVIEW.relative_to(pilot.ROOT))] = pilot.digest(REVIEW.read_bytes())
    arms = {}; negatives = {}
    for arm in ARMS:
        rows = prior['arms'][arm]['benchmarkRows']
        points = [{'id': row['sourceId'], 'group': sources[row['sourceId']]['songNo'],
                   'shape': row['shape'], 'fill': row['fill'], 'prediction': prediction(row['retainedHead'])}
                  for row in rows if row['label'] == 'head']
        if len(points) != 210 or len({r['id'] for r in points}) != 210:
            raise ValueError('incomplete positive cohort')
        negatives[arm] = [len(row['nearbyRetainedHeads']) for row in rows if row['label'] != 'head']
        events = []
        for page in prior['arms'][arm]['pages']:
            events.extend(read_events(pilot.DEFAULT_WORK / 'fa-discrimination-v3' / arm / 'baseline' / page['songNo'] / 'audiveris.log'))
        if {r['pointId'] for r in events} - set(sources):
            raise ValueError('unknown proposal point')
        pairs = paired_proposals(events)
        open_triangles = [row for row in benchmark['rows'] if row['shape'] == 'triangle' and row['fill'] == 'open']
        arms[arm] = {'byPageShapeFill': summarize_points(points),
                     'byShapeFill': summarize_points([{**p, 'group': 'all'} for p in points]),
                     'points': points,
                     'openTriangleLoggedCenterPairs': [{'sourceId': row['id'], **pairs.get(row['id'], {})} for row in open_triangles]}
    heads = prior['arms']['candidate']['headAudit']; rule = prior['protocol']['selectionRule']
    checked_gates = {'triangleFill': threshold_check(heads['triangle']['correctFill'], heads['triangle']['retained'], rule['fillCorrectAmongRetainedTrianglesAtLeast']),
                     'otherHeadRetention': threshold_check(heads['other']['retained'], heads['other']['observed'], rule['nonTriangleHeadRetentionAtLeast'])}
    before = prior['arms']['control']['score']['counts']
    after = prior['arms']['candidate']['score']['counts']
    precision_minimum = Fraction(before['pitchMatches'], before['observedPitched']) - Fraction(str(rule['candidatePitchPrecisionLossAtMost']))
    checked_gates['candidatePitchPrecision'] = {
        **threshold_check(after['pitchMatches'], after['observedPitched'], precision_minimum),
        'evidenceLevel': 'Agreement with unreviewed candidate XML, not source-certified precision.'}
    for name, value in checked_gates.items():
        if (value['status'] == 'pass') != prior['checks'][name]:
            raise ValueError('historical gate mismatch')
    report = {'schemaVersion': 1, 'experiment': 'V3 evaluation diagnostics v4, no recognition changes',
        'sourceCertified': False, 'heldOutRun': False, 'safeToPromote': False,
        'sourceCertifiedPitchPrecision': None,
        'historicalGatesUnchanged': prior['checks'], 'exactCountGates': checked_gates,
        'evidenceLevels': {'headDetectionAndFill': 'Frozen single-AI source observations, not independently certified.',
            'shape': 'Source shape strata versus native labels; ordinary BLACK/VOID do not distinguish round/square/diamond. No four-shape accuracy claim.',
            'timingAndExport': 'Graph scheduling and unique layout witnesses, not source-correct pitch/duration or proof of deletion when ambiguous.',
            'candidateXmlAgreement': 'Unreviewed XML; retained as historical proxy, not gold-source accuracy.',
            'generalization': 'Not measured. All diagnostics use previously exposed training material.',
            'templatePairs': 'Equal logged slim-box center, orientation, anchor and seed path; not forced source-center or identical internal anchor-coordinate evaluations. Correlated proposal counts are not independent observations.'},
        'negativeDiagnostic': negative_diagnostic(negatives), 'arms': arms,
        'retainedUnmatchedReviewQueue': queue,
        'sourceReview': {'selectionSha256': pilot.digest(SELECTION.read_bytes()),
            'reviewSha256': pilot.digest(REVIEW.read_bytes()), 'counts': dict(Counter(r['label'] for r in review['rows'])),
            'rows': review['rows'], 'populationPrecision': None,
            'limitation': selection['scope']},
        'evidenceSha256': evidence,
        'analysisScriptSha256': pilot.digest(Path(__file__).read_bytes()),
        'coreScriptSha256': pilot.digest((pilot.ROOT / 'scripts/omr_point_eval.py').read_bytes())}
    verify_hashes(evidence)
    write_report(output, report)
    print('Source-reviewed retained unmatched sample:', report['sourceReview']['counts'])
    print('Original negative floor:', report['negativeDiagnostic'])
    print('Exact-count gates:', checked_gates)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare-review', action='store_true')
    group.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.prepare_review:
        prepare_review()
    else:
        summarize(args.output)
