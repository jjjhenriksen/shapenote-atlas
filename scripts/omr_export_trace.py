#!/usr/bin/env python3
"""Read-only, receipt-bound graph/export tracing of retained topology proposals.

No recognition, proposal inference or score edits. Research-only additions have
no graph identity: do not call them lost exports or invent a coordinate join.
Layout witnesses establish presence, not source pitch/rhythm correctness.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from pathlib import Path

import omr_head_proposal_study as evidence
import omr_score_audit as audit
import sh1991_fa_survival as survival

load, digest, immutable = evidence.load, evidence.digest, evidence.immutable


def graph_export_rows(sheet, export):
    """Extend the legacy layout recipe only for explicitly labeled pickups.

    The historical helper deliberately excludes every special stack. Its
    ordinary geometry also works on PICKUP stacks when their exact measure
    label exists once per exported part. CAUTIONARY/other specials stay excluded.
    Normalize only an analysis copy; never write or alter the retained graph.
    """
    legacy_rows, legacy = survival.graph_rows(sheet, export)
    working = copy.deepcopy(sheet)
    labels = []
    for stack in working.findall('./page/system/stack'):
        label = stack.get('id')
        if stack.get('special') == 'PICKUP' and all(
                len([m for m in p.findall('measure') if m.get('number') == label]) == 1
                for p in export.findall('part')):
            labels.append(label)
            stack.attrib.pop('special')
    rows, summary = survival.graph_rows(working, export)
    for key, row in rows.items():
        if row['exportWitness']:
            row['witnessKind'] = ('ordinary-layout' if legacy_rows[key]['exportWitness'] else
                                  'pickup-exact-label-layout')
    summary['legacyStages'] = legacy['stages']
    summary['pickupLabelsEligibleForLayoutWitness'] = labels
    return rows, summary


def export_details(root):
    """Actual written events, keyed by the existing witness IDs, not source IDs."""
    inspected = audit.inspect(root)
    segments = {(s['part'], s['measure']): s for s in inspected['segments']}
    result = {}
    for pi, part in enumerate(root.findall('part')):
        for mi, measure in enumerate(part.findall('measure')):
            events = iter(segments[(pi, mi)]['events'])
            for ni, note in enumerate(measure.findall('note')):
                if note.find('grace') is not None:
                    continue
                event = next(events)
                if event['pitch'] is None:
                    continue
                key = f"{part.get('id')}/m{measure.get('number')}/n{ni+1}"
                if key in result:
                    raise ValueError('Duplicate export event identity')
                result[key] = {**event, 'part': part.get('id'),
                               'measureLabel': measure.get('number'),
                               'notehead': note.findtext('notehead'),
                               'lyrics': [n.findtext('text') for n in note.findall('lyric')],
                               'ties': [n.get('type') for n in note.findall('tie')]}
    return result, inspected


def trace_arm(observations, predictions, pairs, graph, exported):
    """Keep every source head and every unpaired prediction in the denominator."""
    source = {r['id']: r for r in observations}
    predicted = {r['id']: r for r in predictions}
    if len(source) != len(observations) or len(predicted) != len(predictions):
        raise ValueError('Duplicate source/prediction identity')
    used_source, used_prediction = set(), set()
    paired = {}
    for pair in pairs:
        sid, pid = pair['sourceId'], pair['predictionId']
        if (sid not in source or pid not in predicted
                or sid in used_source or pid in used_prediction):
            raise ValueError('Invalid or reused geometric pair')
        paired[sid] = predicted[pid]
        used_source.add(sid); used_prediction.add(pid)
    rows = []
    for sid, observed in source.items():
        row = {'sourceId': sid, 'sourceLiteralLabel': observed.get('label'),
               'predictionId': None, 'status': 'not-detected', 'stages': None,
               'exportNote': None, 'exportedEvent': None}
        prediction = paired.get(sid)
        if prediction is not None:
            row.update(predictionId=prediction['id'], origin=prediction['origin'],
                       predictedLiteralLabel=prediction.get('prediction'))
            if prediction['origin'] == 'native':
                raw = str(prediction['rawNativeId'])
                node = graph.get(raw)
                if node is None or f"{node['system']}:{raw}" != prediction['id']:
                    raise ValueError('Native proposal has no exact retained graph identity')
                row['stages'] = {s: node[s] for s in survival.STAGES}
                row['graphId'] = prediction['id']
                row['status'] = ('export-witness' if node['exportWitness'] else
                                 'timed-without-unique-witness' if node['timedSlot'] else
                                 'no-timed-slot')
                if node['exportWitness']:
                    row['exportNote'] = node['exportNote']
                    row['witnessKind'] = node.get('witnessKind', 'ordinary-layout')
                    row['exportedEvent'] = exported[node['exportNote']]
            elif prediction['origin'] in {'image-enclosed-white', 'image-dense-core'}:
                row['status'] = 'not-integrated'
            else:
                raise ValueError('Unknown prediction origin: '+str(prediction['origin']))
        rows.append(row)
    witnesses = [r['exportNote'] for r in rows if r['exportNote'] is not None]
    if len(witnesses) != len(set(witnesses)):
        raise ValueError('Export witness reused across source heads')
    return {
        'sourceHeads': len(rows), 'geometricallyMatched': len(pairs),
        'statusCounts': dict(sorted(Counter(r['status'] for r in rows).items())),
        'stages': {s: sum(bool(r['stages'] and r['stages'][s]) for r in rows)
                   for s in survival.STAGES},
        'unmatchedPredictions': [r['id'] for r in predictions if r['id'] not in used_prediction],
        'rows': rows, 'sourceEventAccuracy': None,
    }


def verify_study(study):
    """Verify the exact artifacts used, without executing a historical runner."""
    study = Path(study).resolve()
    protocol, report, receipt, lock, recognition, labels = [load(study/name) for name in (
        'protocol.json', 'report.json', 'receipt.json', 'inference-lock.json',
        'recognition.json', 'source-observations.json')]
    expected = [(receipt['reportSha256'], 'report.json'),
                (receipt['recognitionSha256'], 'recognition.json'),
                (lock['protocolSha256'], 'protocol.json'),
                (lock['labelsSha256'], 'source-observations.json'),
                (report['protocolSha256'], 'protocol.json'),
                (report['inferenceLockSha256'], 'inference-lock.json'),
                (report['recognitionSha256'], 'recognition.json'),
                (recognition['inferenceLockSha256'], 'inference-lock.json')]
    if any(digest(study/name) != sha for sha, name in expected):
        raise ValueError('Retained report/receipt/lock drift')
    if recognition['status'] != 'graph-ready' or recognition['exitCode'] != 0:
        raise ValueError('No successful retained recognition to trace')
    for name, sha in recognition['artifactsSha256'].items():
        path = (study/name).resolve()
        if study not in path.parents or digest(path) != sha:
            raise ValueError('Retained recognition artifact drift')
    if labels['sourceSha256'] != protocol['sourceSha256'] or not labels['completeHeadCensus']:
        raise ValueError('Source census binding/coverage drift')
    return protocol, report, recognition, labels


def run(study, out):
    study, out = Path(study).resolve(), Path(out).resolve()
    if out == study or study in out.parents or out in study.parents:
        raise ValueError('Keep outputs separate from retained evidence')
    protocol, report, recognition, labels = verify_study(study)
    names = {'protocol.json', 'report.json', 'receipt.json', 'inference-lock.json',
             'recognition.json', 'source-observations.json', *recognition['artifactsSha256']}
    inputs = {str(study/name): digest(study/name) for name in sorted(names)}
    code = {str(Path(m.__file__).resolve()): digest(m.__file__)
            for m in (evidence, audit, audit.archive, audit.archive.pilot, survival,
                      survival.fa)}
    code[str(Path(__file__).resolve())] = digest(__file__)
    exports = [study/name for name in recognition['artifactsSha256'] if name.endswith('.mxl')]
    graph = (study/recognition['graph']).resolve()
    if len(exports) != 1 or str(graph.relative_to(study)) not in recognition['artifactsSha256']:
        raise ValueError('Need exactly one receipt-bound export and graph')
    root = survival.read_xml(exports[0])
    graph_rows, graph_summary = graph_export_rows(survival.read_xml(graph, 'sheet#1/sheet#1.xml'), root)
    exported, structure = export_details(root)
    arms = {arm: {radius: trace_arm(labels['rows'], report['predictions'][arm],
                                  counts['pairs'], graph_rows, exported)
                  for radius, counts in radii.items()}
            for arm, radii in report['arms'].items()
            if arm in {'native', 'native-plus-topology'}}
    if set(arms) != {'native', 'native-plus-topology'}:
        raise ValueError('Both retained native and fused arms are required')
    result = {'schemaVersion': 1, 'source': protocol['source'],
              'phase': 'Read-only trace of consumed retained experiment; no new inference',
              'inputsSha256': inputs, 'codeSha256': code, 'arms': arms,
              'wholeImageGraphExport': graph_summary,
              'wholeExportStructure': structure,
              'sourceEventAccuracy': None, 'wholeScoresAccepted': 0,
              'witnessRecipe': 'Legacy mutually unique layout recipe plus explicitly labeled PICKUP measures; no cautionary witnesses, pitch matching or event correctness inference',
              'sourceCertified': False, 'safeToPromote': False,
              'interpretation': 'Unique layout witnesses establish presence only. Non-integrated proposals are not export deletions. Ambiguous witnesses are unresolved, not proven missing notes.'}
    if any(digest(path) != sha for path, sha in {**inputs, **code}.items()):
        raise ValueError('Input/code drift during trace')
    immutable(out/'report.json', result)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json'),
                                 'inputsSha256': inputs, 'codeSha256': code})
    return result


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    result = run(args.study, args.out)
    print(json.dumps({arm: {r: {'sourceHeads': v['sourceHeads'], 'statusCounts': v['statusCounts']}
                           for r, v in radii.items()} for arm, radii in result['arms'].items()}, indent=2))
