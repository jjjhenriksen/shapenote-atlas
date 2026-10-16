#!/usr/bin/env python3
"""Apply terminal-supported grid and frozen crop scorer to native head boxes.

Existing score auditing stays unchanged. This is a separately versioned shadow
adapter; it never edits MusicXML or equates native IDs with exported notes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import omr_followup_study as study
import omr_grid_alignment as alignment
import omr_measure_worklist as native
import omr_terminal_grid as terminal


def run(manifest_path, score_path, out, model_study=None):
    from PIL import Image
    manifest_path, score_path, out = map(Path, (manifest_path, score_path, out))
    raw = alignment.run(manifest_path, score_path, out/'raw-grid')
    manifest = study.prior.prior.load(manifest_path)
    def path(name):
        p = Path(manifest[name]['path'])
        return p if p.is_absolute() else manifest_path.parent/p
    model = None
    if model_study is not None:
        model_study = Path(model_study)
        study.check(model_study)
        model = study.prior.prior.load(model_study/'transfer-protocol.json')
        if model != study.freeze(model_study):
            raise ValueError('Frozen model selection drift')
    protocol = {'rawAlignmentSha256': study.prior.archive.digest(out/'raw-grid/alignment.json'),
                'terminalRecipe': terminal.RECIPE, 'scoringRecipe': study.scoring.RECIPE,
                'modelSelectionSha256': study.prior.archive.digest(model_study/'transfer-protocol.json') if model else None,
                'codeSha256': {Path(m.__file__).name: study.prior.archive.digest(m.__file__)
                               for m in (terminal, native, study, study.scoring, study.prior.classifier)}}
    protocol['codeSha256'][Path(__file__).name] = study.prior.archive.digest(__file__)
    study.prior.archive.immutable(out/'protocol.json', study.prior.archive.json_bytes(protocol))
    target = out/'worklist.json'
    if target.exists():
        report = study.prior.prior.load(target)
        if report['protocolSha256'] != study.prior.archive.digest(out/'protocol.json'):
            raise ValueError('Native terminal worklist binding drift')
        return report
    bands = study.prior.prior.load(path('bands'))['bands']
    with Image.open(path('source')) as image:
        refined = terminal.refine(image, raw['imageGrid'])
        aligned = alignment.align(refined, raw['draftStacks'], bands)
        staff_ids, heads = native.native_heads(path('graph'), manifest['sheetNumber'], manifest['systemId'])
        report = native.assign(heads, aligned['proposedSpans'], bands, staff_ids, refined['staffLattices'])
        if model is not None:
            bank = study.scoring.fit(study.prior.baseline.samples())
            for head in report['heads']:
                if head['status'] == 'localized-proposal':
                    crop = study.prior.classifier.crop(image, head['x'], head['y'], head['interline'])
                    head['shadowClassification'] = study.scoring.predict(crop, bank)[model['selectedArm']]
    for name in ('source', 'graph', 'bands'):
        if study.prior.archive.digest(path(name)) != manifest[name]['sha256']:
            raise ValueError('Native terminal worklist input drift')
    if study.prior.archive.digest(score_path) != manifest['scoreSha256']:
        raise ValueError('Score drift')
    if model_study is not None:
        study.check(model_study)
    report.update(protocolSha256=study.prior.archive.digest(out/'protocol.json'),
                  gridAlignment=aligned, selectedArm=model['selectedArm'] if model else None,
                  sourceAccuracy=None, measuredHumanEdits=None, measuredHumanMinutes=None,
                  recognizerChanged=False, scoreChanged=False, safeToPromote=False)
    study.prior.archive.immutable(target, study.prior.archive.json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--grid-manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model-study', type=Path)
    args = parser.parse_args()
    result = run(args.grid_manifest, args.score, args.out, args.model_study)
    print(json.dumps({'nativeHeads': result['nativeHeads'], 'counts': result['counts'],
                      'grid': result['gridAlignment']['boundaryComparison'], 'selectedArm': result['selectedArm']}))
