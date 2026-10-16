#!/usr/bin/env python3
"""Replay training-only barline diagnostics; never invoke recognition."""
import argparse
from collections import Counter
from pathlib import Path
import re

import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
import sh1991_fa_survival as survival
from sh1991_head_audit import heads_in_graph, match, write_report

WORK = pilot.DEFAULT_WORK / 'barline-v2'


def parse_trace(text):
    snapshots = {}; removals = []; conflicts = []; active_stage = None
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.startswith('BARTRACE|'):
            p = line.split('|')
            if len(p) != 12:
                raise ValueError('malformed bar snapshot')
            stage, phase = p[1:3]
            active_stage = stage
            record = dict(zip(('system', 'id', 'staff', 'glyph', 'x', 'y', 'width', 'height'), map(int, p[3:11])))
            record['grade'] = float(p[11]); record['line'] = line_no
            snapshots.setdefault(stage + '/' + phase, []).append(record)
        elif line.startswith('BARCOUNT|'):
            p = line.split('|'); active_stage = p[1]
            snapshots.setdefault(p[1] + '/' + p[2], [])
        elif line.startswith('BARREMOVE|'):
            removals.append({'line': line_no, 'stage':active_stage, 'id': int(line.split('|')[1]), 'callPath': line.split('|')[-1]})
        elif line.startswith('BARCONFLICT|'):
            fields = dict(p.split('=', 1) for p in line.split('|')[1:])
            supports = fields.get('stemHeads')
            shapes = re.findall(r'\bNOTEHEAD_[A-Z_]+\b', supports or '')
            fields.pop('stemHeads', None)  # Raw text remains in the hash-bound log.
            conflicts.append({'line':line_no, 'stage':active_stage, **fields,
                              'stemHeadIds':re.findall(r'HeadInter#(\d+)', supports or '') if supports is not None else None,
                              'supportShapes':shapes if supports is not None else None,
                              'faOnlyStemSupport':bool(shapes) and all(s.startswith('NOTEHEAD_FA_') for s in shapes)})
    for key in ('HEADS/ENTER', 'HEADS/EXIT', 'STEMS/EXIT', 'REDUCTION/EXIT', 'MEASURES/ENTER', 'MEASURES/EXIT'):
        if key not in snapshots:
            raise ValueError('missing completed stage: ' + key)
    for records in snapshots.values():
        if len({(r['system'], r['id']) for r in records}) != len(records):
            raise ValueError('duplicate physical bar identity within stage')
    return {'snapshots': snapshots, 'counts': {k: len(v) for k, v in snapshots.items()},
            'removals': removals, 'conflicts':conflicts}


def geometry(records):
    """No generated IDs in cross-run matching; include glyph and full source box."""
    return sorted(tuple(r[k] for k in ('system', 'staff', 'glyph', 'x', 'y', 'width', 'height')) for r in records)


def compact_trace(trace):
    """Keep all stages as inventory deltas, not forty repeated full inventories."""
    columns = ('system', 'id', 'staff', 'glyph', 'x', 'y', 'width', 'height', 'grade')
    inventory = []; lookup = {}; previous = set(); deltas = {}
    for stage, records in trace['snapshots'].items():
        indices = set()
        for record in records:
            key = tuple(record[k] for k in columns)
            if key not in lookup:
                lookup[key] = len(inventory); inventory.append(list(key))
            indices.add(lookup[key])
        lines = [r['line'] for r in records]
        deltas[stage] = {'added':sorted(indices - previous), 'removed':sorted(previous - indices),
                         'logLineRange':[min(lines), max(lines)] if lines else None}
        previous = indices
    call_paths = list(dict.fromkeys(r['callPath'] for r in trace['removals']))
    removals = [{k:v for k,v in r.items() if k != 'callPath'} | {'callPathIndex':call_paths.index(r['callPath'])}
                for r in trace['removals']]
    return {k:v for k,v in trace.items() if k not in ('snapshots', 'removals')} | {
        'removalCallPaths':call_paths, 'removals':removals,
        'inventoryColumns':list(columns), 'physicalBarInventory':inventory, 'snapshotDeltas':deltas}


def summarize(work, output):
    protocol = pilot.load(work / 'protocol.json')
    parent = pilot.load(pilot.DEFAULT_WORK / 'dataset.json')
    original = pilot.load(work / 'original-inventory.json')
    for path, sha in original.items():
        if pilot.digest((pilot.ROOT / path).read_bytes()) != sha:
            raise ValueError('original artifact changed: ' + path)
    if pilot.digest((pilot.DEFAULT_WORK / 'dataset.json').read_bytes()) != protocol['parentDatasetSha256']:
        raise ValueError('parent dataset drift')
    audit_path = pilot.ROOT / 'docs/experiments/sh1991-head-shape-audit-20261015.json'
    if pilot.digest(audit_path.read_bytes()) != protocol['headAuditSha256']:
        raise ValueError('source-head audit drift')
    frozen_inputs = pilot.load(work / 'frozen-inputs.json')
    for path, sha in frozen_inputs.items():
        if pilot.digest((pilot.ROOT / path).read_bytes()) != sha:
            raise ValueError('frozen experiment metadata/patch/test drift: ' + path)
    _, observations = fa.audited_rows()
    arms = {}; evidence = {}
    engine_metadata = {name:pilot.load(work / ('engine-' + name + '.json')) for name in ('diagnostic', 'guard', 'stemguard')}
    for arm in ('off', 'on', 'guard-off', 'stemguard-off', 'revised'):
        directory = work / arm
        pilot.verify(directory)
        survival.verify_training_cohort(pilot.load(directory / 'dataset.json'), parent, protocol['trainingProbe'])
        results = pilot.load(directory / 'baseline-results.json')
        receipts = results['records']
        engine = engine_metadata['diagnostic' if arm in ('off', 'on') else 'guard' if arm == 'guard-off' else 'stemguard']
        identity = engine['engineIdentity']
        if arm in ('stemguard-off', 'revised'):
            config = pilot.load(directory / 'execution.json')
            expected_opts = '-Datlas.barTrace=true -Datlas.faStemBarGuard=' + str(arm == 'revised').lower()
            if config['JAVA_OPTS'] != expected_opts or config['engineIdentity'] != identity:
                raise ValueError('JVM property or environment engine drift')
        if len(receipts) != len(protocol['trainingProbe']) or {r['songNo'] for r in receipts} != set(protocol['trainingProbe']):
            raise ValueError('incomplete/duplicate training results')
        pages = []; totals = Counter(); topology = Counter(); cohorts = {'triangle': Counter(), 'other': Counter()}
        for receipt in receipts:
            if receipt['engineIdentity'] != identity or pilot.engine_identity(Path(receipt['command'][0])) != identity:
                raise ValueError('engine drift')
            song = receipt['songNo']; page_dir = directory / 'baseline' / song
            if receipt != pilot.load(page_dir / 'run.json'):
                raise ValueError('aggregate receipt mismatch')
            required = 'org.audiveris.omr.sheet.ProcessingSwitches.faHeads=' + str(arm != 'off').lower()
            if required not in receipt['command']:
                raise ValueError('wrong fa arm')
            graphs = list(page_dir.glob('*.omr'))
            if len(graphs) != 1:
                raise ValueError('expected one saved graph')
            graph = graphs[0]; export = pilot.ROOT / receipt['output']; log = page_dir / 'audiveris.log'
            for path in (graph, export, log, page_dir / 'run.json'):
                evidence[str(path.relative_to(pilot.ROOT))] = pilot.digest(path.read_bytes())
            sheet = survival.read_xml(graph, 'sheet#1/sheet#1.xml')
            rows, summary = survival.graph_rows(sheet, survival.read_xml(export))
            trace = parse_trace(log.read_text())
            hits = match([r for r in observations if r['songNo'] == song], heads_in_graph(sheet), .5)
            source_rows = []
            for source in [r for r in observations if r['songNo'] == song]:
                head = hits.get(source['id']); record = rows[head['id']] if head else None
                name = 'triangle' if source['shape'] == 'triangle' else 'other'
                cohorts[name]['observed'] += 1
                for stage in survival.STAGES:
                    cohorts[name][stage] += bool(record and record[stage])
                source_rows.append({'observation': source['id'], 'shape': source['shape'], 'head': record})
            totals.update(summary['stages']); topology.update(summary['topology'])
            old = next(r for r in pilot.load(fa.WORK / ('off' if arm == 'off' else 'on') / 'baseline-results.json')['records'] if r['songNo'] == song)
            comparison = pilot.compare(pilot.score((pilot.ROOT / old['output']).read_bytes()), pilot.score(export.read_bytes()))
            pages.append({'songNo': song, 'trace': trace, **summary, 'sourceHeads': source_rows,
                          'matchesFrozenV1WrittenEvents': comparison['exactWrittenEvents'] and comparison['measureCountsMatch']})
        arms[arm] = {'score': results['summary']['all'], 'headAudit': fa.head_statistics(directory),
                     'stages': dict(totals), 'topology': dict(topology), 'sourceCohorts': {k:dict(v) for k,v in cohorts.items()}, 'pages': pages}
    comparisons = []
    for off in arms['off']['pages']:
        song = off['songNo']; on = next(r for r in arms['on']['pages'] if r['songNo'] == song)
        revised = next(r for r in arms['revised']['pages'] if r['songNo'] == song)
        divergence = next((stage for stage in off['trace']['snapshots']
                           if geometry(off['trace']['snapshots'][stage]) != geometry(on['trace']['snapshots'][stage])), None)
        before = set(geometry(on['trace']['snapshots']['REDUCTION/EXIT']))
        after = set(geometry(revised['trace']['snapshots']['REDUCTION/EXIT']))
        comparisons.append({'songNo': song, 'firstGeometryDivergence': divergence,
                            'revisedRestoredPhysicalBarsAtReduction':len(after-before),
                            'revisedNewPhysicalBarLossesAtReduction':len(before-after)})
    gates = fa.gate(protocol['selectionRule'], arms['off']['score'], arms['revised']['score'],
                    arms['off']['headAudit'], arms['revised']['headAudit'],
                    all(p['matchesFrozenV1WrittenEvents'] for p in arms['off']['pages']))
    for arm in ('off', 'on', 'guard-off', 'stemguard-off'):
        if not all(p['matchesFrozenV1WrittenEvents'] for p in arms[arm]['pages']):
            raise ValueError('diagnostic-only arm does not reproduce frozen v1 events')
    for arm in ('guard-off', 'stemguard-off'):
        if any(arms[arm][key] != arms['on'][key] for key in ('score', 'headAudit', 'stages', 'topology', 'sourceCohorts')):
            raise ValueError('default-off confirmation differs from current fa prototype')
    for arm_name, arm in arms.items():
        for page in arm['pages']:
            page['measureLog'] = survival.log_evidence((work / arm_name / 'baseline' / page['songNo'] / 'audiveris.log').read_text())
            page['trace'] = compact_trace(page['trace'])
            if arm_name in ('guard-off', 'stemguard-off'):
                # These validation arms duplicate v1-on's final survival metrics.
                # Retain counts/conflicts/receipts; primary three arms carry full
                # numeric inventories and per-source-head rows.
                page.pop('sourceHeads')
                for key in ('inventoryColumns', 'physicalBarInventory', 'snapshotDeltas'):
                    page['trace'].pop(key)
                page['trace']['inventoryOmittedForConfirmationArm'] = True
    report = {'schemaVersion':1, 'protocol':protocol, 'engines':engine_metadata,
              'javaTests':pilot.load(work/'java-tests.json'),
              'executionEnvironments':{arm:pilot.load(work/arm/'execution.json') for arm in ('stemguard-off','revised')},
              'design':pilot.load(work/'stemguard-design.json'), 'arms':arms, 'comparisons': comparisons,
              'checks':gates, 'passesAllTrainingGates':all(gates.values()), 'safeToPromote':False,
              'sourceCertified':False, 'heldOutRun':False, 'originalFilesUnchanged':len(original),
              'frozenInputsSha256':frozen_inputs, 'evidenceSha256': evidence,
              'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes())}
    for path, sha in evidence.items():
        if pilot.digest((pilot.ROOT/path).read_bytes()) != sha:
            raise ValueError('artifact changed during analysis')
    write_report(output, report)
    print({a:{'score':v['score'], 'stages':v['stages'], 'topology':v['topology'], 'sourceCohorts':v['sourceCohorts']} for a,v in arms.items()})
    print('First divergence:', comparisons, 'Gates:', gates)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=WORK)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); summarize(args.work, args.output)
