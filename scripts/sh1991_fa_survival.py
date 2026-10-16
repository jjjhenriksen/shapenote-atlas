#!/usr/bin/env python3
"""Read-only attribution of saved fa-v1 graph, rhythm and export losses.

Final snapshots are not per-step execution traces. Export witnesses use unique
layout coordinates, never candidate score pitches or source-derived shapes.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET

import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
from sh1991_head_audit import heads_in_graph, match, write_report

OUTPUT = pilot.ROOT / 'docs/experiments/sh1991-fa-survival-20261015.json'
STAGES = ('retained', 'headStem', 'chord', 'chordStem', 'sharedStem', 'measure', 'voiceBegin', 'timedSlot', 'exportWitness')


def tokens(node, path):
    return (node.findtext(path) or '').split() if node is not None else []


def read_xml(path, member=None):
    data = path.read_bytes()
    if data[:2] == b'PK':
        with zipfile.ZipFile(path) as archive:
            if member is None:
                container = ET.fromstring(archive.read('META-INF/container.xml'))
                member = next(n.attrib['full-path'] for n in container.iter()
                              if n.tag.rsplit('}', 1)[-1] == 'rootfile')
            data = archive.read(member)
    root = ET.fromstring(data)
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    return root


def exported_notes(root):
    notes = []
    for part in root.findall('part'):
        for measure in part.findall('measure'):
            for index, note in enumerate(measure.findall('note')):
                if note.find('pitch') is None or note.find('grace') is not None:
                    continue
                notes.append({'id': f"{part.get('id')}/m{measure.get('number')}/n{index+1}",
                              'part': part.get('id'), 'measure': measure.get('number'),
                              'voice': note.findtext('voice', '1'), 'staff': note.findtext('staff', '1'),
                              'x': float(note.get('default-x')) if note.get('default-x') is not None else None})
    if len({n['id'] for n in notes}) != len(notes):
        raise ValueError('duplicate export measure/note identities; cannot witness safely')
    return notes


def unique_export_witnesses(rows, notes):
    """Mutually unique layout matches only; collisions remain unresolved."""
    by_context = defaultdict(list)
    for note in notes:
        by_context[tuple(note[k] for k in ('part', 'measure', 'voice', 'staff'))].append(note)
    candidates = {}; reverse = defaultdict(list)
    for key, row in rows.items():
        if row.get('exportContext') is None or row.get('expectedExportX') is None:
            continue
        matches = [n for n in by_context[tuple(row['exportContext'])]
                   if n['x'] is not None and abs(n['x'] - row['expectedExportX']) <= 1]
        candidates[key] = matches
        for note in matches:
            reverse[note['id']].append(key)
    return {key: matches[0]['id'] for key, matches in candidates.items()
            if len(matches) == 1 and len(reverse[matches[0]['id']]) == 1}, candidates


def graph_rows(sheet, export):
    rows = {}; systems = []; topology = Counter(); anomalies = Counter()
    scale = sheet.find('./scale/interline')
    if scale is None or float(scale.get('main', '0')) <= 0:
        raise ValueError('missing interline scale')
    interline = float(scale.get('main'))
    export_parts = [p.get('id') for p in export.findall('part')]
    for system in sheet.findall('./page/system'):
        nodes = {n.get('id'): n for n in system.findall('./sig/inters/*') if n.get('id') is not None}
        members = defaultdict(set); head_stems = defaultdict(set); chord_stems = defaultdict(set)
        for relation in system.findall('./sig/relations/relation'):
            a, b = relation.get('source'), relation.get('target')
            if a not in nodes or b not in nodes:
                anomalies['danglingRelations'] += 1
                continue
            if relation.find('containment') is not None:
                # The saved format is ensemble -> member. Accept the reversed
                # direction only when node types unambiguously identify it.
                for parent, child in ((a, b), (b, a)):
                    if (nodes[parent].tag, nodes[child].tag) in (('head-chord', 'head'), ('staff-barline', 'barline')):
                        members[parent].add(child)
            for tag, target, kind in [('head-stem', head_stems, 'head'), ('chord-stem', chord_stems, 'head-chord')]:
                if relation.find(tag) is not None:
                    for parent, child in ((a, b), (b, a)):
                        if nodes[parent].tag == kind and nodes[child].tag == 'stem':
                            target[parent].add(child)
        chords = {key: n for key, n in nodes.items() if n.tag == 'head-chord'}
        head_chords = defaultdict(set)
        for chord in chords:
            for head in members[chord]:
                if nodes[head].tag == 'head':
                    head_chords[head].add(chord)
        contexts = defaultdict(list)
        stacks = system.findall('stack'); parts = system.findall('part')
        # This bounded witness recipe is deliberately restricted to the existing
        # single-staff P1..Pn cohort, not a general physical/logical part resolver.
        if [f"P{p.get('id')}" for p in parts] != export_parts or any(len(p.findall('staff')) != 1 for p in parts):
            raise ValueError('unsupported part/staff mapping for layout witnesses')
        for part in parts:
            staff = part.find('staff'); previous = None
            measures = part.findall('measure')
            if len(measures) != len(stacks):
                raise ValueError('measure/stack order differs; cannot assign context')
            for measure, stack in zip(measures, stacks):
                left = measure.find('left-barline')
                if left is None:
                    left = previous.find('right-barline') if previous is not None else part.find('left-barline')
                left_refs = tokens(left, 'staff-barlines')
                left_x = None
                if left is None:
                    left_x = float(staff.get('left'))
                elif len(left_refs) == 1 and left_refs[0] in nodes:
                    bar = nodes[left_refs[0]]
                    physical = [nodes[k] for k in members[left_refs[0]] if nodes[k].tag == 'barline']
                    if physical:
                        left_x = max(int(n.find('bounds').get('x')) + int(n.find('bounds').get('w')) // 2 for n in physical)
                    elif bar.find('bounds') is not None:
                        bounds = bar.find('bounds')
                        left_x = int(bounds.get('x')) + int(bounds.get('w')) - 1
                slot_times = {s.get('id'): s.get('time-offset') for s in stack.findall('slot')}
                begins = defaultdict(list)
                for voice in measure.findall('voice'):
                    for entry in voice.findall('./slots/entry'):
                        value = entry.find('value')
                        if value is not None and value.get('status') == 'BEGIN':
                            slot = entry.findtext('key')
                            time = slot_times.get(slot)
                            if time is not None:
                                if Fraction(time) < 0:
                                    raise ValueError('negative saved slot time')
                            begins[value.get('chord')].append({'voice': voice.get('id'), 'slot': slot, 'time': time})
                for chord in tokens(measure, 'head-chords'):
                    contexts[chord].append({'system': system.get('id'), 'part': f"P{part.get('id')}",
                        'measure': stack.get('id'), 'special': stack.get('special'),
                        'leftX': left_x, 'abnormal': measure.get('abnormal') == 'true', 'begins': begins[chord]})
                previous = measure
        for key, node in nodes.items():
            if node.tag != 'head':
                continue
            if key in rows:
                raise ValueError('reused head id across systems')
            chord_ids = sorted(head_chords[key])
            row = {'id': key, 'system': system.get('id'), 'shape': node.get('shape'),
                   'staff': node.get('staff'), 'retained': True, 'headStem': bool(head_stems[key]),
                   'chord': bool(chord_ids), 'chordIds': chord_ids, 'chordStem': False, 'sharedStem': False,
                   'measure': False, 'voiceBegin': False, 'timedSlot': False, 'exportWitness': False,
                   'exportContext': None, 'expectedExportX': None}
            if len(chord_ids) > 1:
                anomalies['headsInMultipleChords'] += 1
            if len(chord_ids) == 1:
                chord = chord_ids[0]; row['chordStem'] = bool(chord_stems[chord])
                row['sharedStem'] = bool(head_stems[key] & chord_stems[chord])
                if len(contexts[chord]) > 1:
                    anomalies['chordsInMultipleMeasures'] += 1
                if len(contexts[chord]) == 1:
                    context = contexts[chord][0]; row['measure'] = True
                    row['measureContext'] = {k: context[k] for k in ('system', 'part', 'measure', 'abnormal')}
                    row['voiceBegin'] = bool(context['begins'])
                    if len(context['begins']) == 1:
                        begin = context['begins'][0]; row['timedSlot'] = begin['time'] is not None
                        row['rhythm'] = begin
                        if row['timedSlot'] and context['special'] is None:
                            row['exportContext'] = [context['part'], context['measure'], begin['voice'], '1']
                            if context['leftX'] is not None:
                                row['expectedExportX'] = round(10 * (int(node.find('bounds').get('x')) - context['leftX']) / interline)
            rows[key] = row
        count = Counter(n.tag for n in nodes.values())
        summary = {'system': system.get('id'), 'stacks': len(stacks),
                   'cautionaryStacks': sum(s.get('special') == 'CAUTIONARY' for s in stacks),
                   'barlines': count['barline'], 'staffBarlines': count['staff-barline'],
                   'heads': count['head'], 'headChords': count['head-chord'],
                   'multiHeadChords': sum(len(members[c]) > 1 for c in chords),
                   'chordsWithFourOrMoreHeads': sum(len(members[c]) >= 4 for c in chords),
                   'abnormalMeasures': sum(m.get('abnormal') == 'true' for p in parts for m in p.findall('measure'))}
        systems.append(summary)
        topology.update({k: v for k, v in summary.items() if k != 'system'})
    notes = exported_notes(export)
    witnesses, candidates = unique_export_witnesses(rows, notes)
    for key, row in rows.items():
        row['exportWitness'] = key in witnesses
        if key in witnesses:
            row['exportNote'] = witnesses[key]
        elif key in candidates:
            row['exportCandidateCount'] = len(candidates[key])
    summary = {stage: sum(r[stage] for r in rows.values()) for stage in STAGES}
    summary.update(exportedTimedPitched=len(notes),
                   exportedTimedWithoutUniqueGraphWitness=len(notes)-len(witnesses),
                   timedWithoutUniqueExportWitness=sum(r['timedSlot'] and not r['exportWitness'] for r in rows.values()))
    return rows, {'stages': summary, 'topology': dict(topology), 'systems': systems, 'anomalies': dict(anomalies)}


def log_evidence(text):
    actions = []; warnings = []
    for index, line in enumerate(text.splitlines(), 1):
        action = re.search(r'MeasuresBuilder\s+\d+\s+\|\s+S(\d+)\s+(deleting\s+(?:minor|half)|expanding\s+major) column:(.*)', line)
        if action:
            actions.append({'line': index, 'system': action[1], 'action': ' '.join(action[2].split()), 'column': action[3].strip()})
        if re.search(r'\bWARN\s+\[.*(?:StackRhythm|PartwiseBuilder|afterReload)', line):
            warnings.append({'line': index, 'text': line.split('|', 1)[-1].strip()})
    return {'columnActions': actions, 'warningLines': warnings,
            'columnActionCounts': dict(Counter(a['action'] for a in actions))}


def verify_training_cohort(dataset, parent, probe):
    rows = dataset['records']; expected = {r['songNo']: r for r in parent['records'] if r['songNo'] in probe}
    if len(rows) != len(probe) or {r['songNo'] for r in rows} != set(probe) or any(r['split'] != 'train' for r in rows):
        raise ValueError('only frozen training probe is allowed')
    if any(row != expected.get(row['songNo']) for row in rows):
        raise ValueError('training source/label metadata differs from frozen parent')


def summarize(work, output):
    frozen = pilot.load(fa.FROZEN_REPORT); protocol = frozen['protocol']
    if pilot.digest((pilot.DEFAULT_WORK/'dataset.json').read_bytes()) != protocol['parentDatasetSha256']:
        raise ValueError('original dataset drift')
    parent = pilot.load(pilot.DEFAULT_WORK/'dataset.json')
    audit_path = pilot.ROOT/'docs/experiments/sh1991-head-shape-audit-20261015.json'
    if pilot.digest(audit_path.read_bytes()) != protocol['headAuditSha256']:
        raise ValueError('source-head audit drift')
    audit, observations = fa.audited_rows()
    result = {}; file_hashes = {}
    for arm in ('off', 'on'):
        directory = work/arm; pilot.verify(directory)
        dataset = pilot.load(directory/'dataset.json')
        verify_training_cohort(dataset, parent, protocol['trainingProbe'])
        pages = []; totals = Counter(); topology = Counter()
        receipts = pilot.load(directory/'baseline-results.json')['records']
        if len(receipts) != len(protocol['trainingProbe']) or {r['songNo'] for r in receipts} != set(protocol['trainingProbe']):
            raise ValueError('incomplete or duplicated result cohort')
        for receipt in receipts:
            if receipt['engineIdentity'] != frozen['engine']['engineIdentity']:
                raise ValueError('engine receipt drift')
            required = 'org.audiveris.omr.sheet.ProcessingSwitches.faHeads=' + str(arm == 'on').lower()
            if required not in receipt['command']:
                raise ValueError('wrong arm switch')
            song = receipt['songNo']; page_dir = directory/'baseline'/song
            if pilot.load(page_dir/'run.json') != receipt:
                raise ValueError('per-image receipt differs from aggregate result')
            graphs = list(page_dir.glob('*.omr'))
            if len(graphs) != 1:
                raise ValueError('expected one graph archive')
            graph, export, log = graphs[0], pilot.ROOT/receipt['output'], page_dir/'audiveris.log'
            pointers = {}
            for kind, path in [('graph', graph), ('export', export), ('log', log), ('run', page_dir/'run.json')]:
                sha = pilot.digest(path.read_bytes()); file_hashes[path] = sha
                pointers[kind] = {'path': str(path.relative_to(pilot.ROOT)), 'sha256': sha}
            sheet = read_xml(graph, 'sheet#1/sheet#1.xml')
            rows, summary = graph_rows(sheet, read_xml(export))
            if summary['stages']['exportedTimedPitched'] != receipt['metrics']['counts']['observedPitched']:
                raise ValueError('export note accounting differs from original evaluator')
            selected = [r for r in observations if r['songNo'] == song]
            hits = match(selected, heads_in_graph(sheet), .5)
            source_rows = []
            for source in selected:
                head = hits.get(source['id'])
                source_rows.append({'observation': source['id'], 'shape': source['shape'], 'fill': source['fill'],
                                    'head': rows[head['id']] if head else None})
            cohorts = {}
            for name, selection in [('triangle', [r for r in source_rows if r['shape'] == 'triangle']),
                                    ('other', [r for r in source_rows if r['shape'] != 'triangle'])]:
                cohorts[name] = {'observed': len(selection), **{stage: sum(bool(r['head'] and r['head'][stage]) for r in selection) for stage in STAGES}}
            page = {'songNo': song, 'artifacts': pointers, **summary, 'logs': log_evidence(log.read_text()),
                    'sourceAuditCohorts': cohorts, 'sourceAuditRows': source_rows}
            pages.append(page); totals.update(summary['stages']); topology.update(summary['topology'])
        cohort_totals = {cohort: dict(sum((Counter(p['sourceAuditCohorts'][cohort]) for p in pages), Counter()))
                         for cohort in ('triangle', 'other')}
        action_totals = dict(sum((Counter(p['logs']['columnActionCounts']) for p in pages), Counter()))
        result[arm] = {'stages': dict(totals), 'topology': dict(topology),
                       'sourceAuditCohorts': cohort_totals, 'columnActionCounts': action_totals, 'pages': pages}
    if any(pilot.digest(path.read_bytes()) != sha for path, sha in file_hashes.items()):
        raise ValueError('artifacts changed during analysis')
    source_repo = pilot.DEFAULT_WORK/'toolchain/audiveris-fa-v1/app/src/main/java/org/audiveris/omr'
    code_evidence = []
    for relative, symbols in [('sheet/rhythm/MeasuresBuilder.java', ['enforceSystemConsistency', 'Column.delete']),
                              ('score/PartwiseBuilder.java', ['processMeasure', 'processChord', 'processNote', 'toTenths']),
                              ('sheet/rhythm/Measure.java', ['getAbscissa', 'getPartBarlineOn']),
                              ('sig/inter/StaffBarlineInter.java', ['getRightX'])]:
        path = source_repo/relative
        code_evidence.append({'path': str(path.relative_to(pilot.ROOT)), 'sha256': pilot.digest(path.read_bytes()),
                              'upstreamCommit': frozen['engine']['upstreamCommit'], 'symbols': symbols})
    report = {'schemaVersion': 1, 'experiment': 'fa-v1 saved-artifact stage survival',
              'parentReportSha256': pilot.digest(fa.FROZEN_REPORT.read_bytes()),
              'sourceAuditSha256': protocol['headAuditSha256'], 'codeEvidence': code_evidence, 'arms': result,
              'analysisScriptSha256': pilot.digest(Path(__file__).read_bytes()),
              'analysisDependencies': {name: pilot.digest((pilot.ROOT/'scripts'/name).read_bytes())
                                       for name in ('sh1991_pilot.py', 'sh1991_fa_experiment.py', 'sh1991_head_audit.py')},
              'recognitionRerun': False, 'engineModified': False, 'heldOutRun': False, 'sourceCertified': False,
              'method': 'Final graph containment + measure head-chord lists + voice BEGIN with saved timed slot. Export witnesses require mutually unique part/measure-label/voice/staff/default-x within 1 tenth; no pitch or shape matching. Single-staff P1..Pn cohort only.',
              'limitations': ['Final graphs are not intermediate execution snapshots; no proof of the first deletion stage.',
                              'Export witnesses are layout-based attribution, not source correctness or persistent note IDs; ambiguous/missing witnesses stay unresolved.',
                              'All-head counts include unreviewed detections; only the frozen 210 observations have source-literal review (single AI).',
                              'Cautionary stacks are counted and reported separately; grace notes excluded from timed exports.',
                              'Candidate rhythm slots do not establish correct source onset, duration, or measure topology.']}
    write_report(output, report)
    for arm in result:
        print(arm, 'stages', result[arm]['stages'], 'topology', result[arm]['topology'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=fa.WORK)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    summarize(args.work, args.output)
