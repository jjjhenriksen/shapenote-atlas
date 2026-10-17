#!/usr/bin/env python3
"""Read-only development study on the CONSUMED SH2025/219 census.

No old study runner, recognition, score write, source download or reserved
source inspection. Raw inputs/predictions remain local; publish aggregates only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import omr_head_proposals as detector
import omr_localization_eval as evaluation
import omr_training_population as training

ROOT = Path(__file__).resolve().parents[1]
PRIOR = Path('work/model-pilot/sh1991-v1/expanded-localization-v1')
SOURCE = Path('work/source-images/2025/219-he-hath-saved-us-4c1ffc8918.jpg')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def immutable(path, value):
    path = Path(path)
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Frozen development artifact drift; use a new output directory')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as saved:
        saved.write(data)


def source_paths(retained):
    """Resolve only the seven already-consumed exemplar sources."""
    selection = retained/'docs/experiments/sh1991-eval-review-selection-20261015.json'
    paths = {r['sha256']: retained/r['path'] for r in load(selection)['sourceImages'].values()}
    for name in ('501t-penn-8a2061599c.jpg', '184-and-jesus-crucified-bb8d27f0da.jpg',
                 '188-ephesus-aa1817a576.jpg', '80t-troubles-over-604fc47469.jpg'):
        path = retained/'work/source-images/2025'/name
        paths[digest(path)] = path
    if len(paths) != 7:
        raise ValueError('Need seven distinct consumed exemplar source hashes')
    return paths, selection


def protocol(retained):
    import numpy
    from PIL import __version__ as pillow
    paths, selection = source_paths(retained)
    inputs = [retained/SOURCE, selection, *paths.values()]
    inputs += [retained/PRIOR/name for name in (
        'source-observations.json', 'report.json', 'population-manifest.json',
        'recognition.json', 'inference-lock.json', 'transfer-protocol.json',
        'development-protocol.json')]
    # Bind raw bytes as well as the receipt: completed analysis must reject
    # artifact drift too, even though it never opens a graph for recognition.
    inputs += [retained/name for name in
               load(retained/PRIOR/'recognition.json')['artifactsSha256']]
    return {
        'phase': 'consumed development only; not a pre-source or held-out freeze',
        'recipe': detector.RECIPE, 'matchingRecipe': evaluation.RECIPE,
        'numpyVersion': numpy.__version__, 'pillowVersion': pillow,
        'retainedInputsSha256': {str(p.relative_to(retained)): digest(p) for p in inputs},
        'codeSha256': {str(Path(m.__file__).relative_to(ROOT)): digest(m.__file__)
                      for m in (detector, detector.geometry, evaluation, training,
                                training.prior.classifier, training.ranking)},
        'runnerSha256': digest(__file__),
        'primaryArm': 'native-plus-selective-squares',
        'baseline': 'exact archived expanded-bank predictions; no native engine rerun',
        'training': '373 archived exemplars on seven consumed pages; never add 219',
        'sourceCertified': False, 'safeToPromote': False,
    }


def retained_evidence(retained):
    """Verify the retained evidence chain without executing frozen code."""
    prior = retained/PRIOR
    labels, report = load(prior/'source-observations.json'), load(prior/'report.json')
    receipt, lock = load(prior/'recognition.json'), load(prior/'inference-lock.json')
    frozen, development = load(prior/'transfer-protocol.json'), load(prior/'development-protocol.json')
    if (lock['labelsSha256'] != digest(prior/'source-observations.json')
            or lock['transferProtocolSha256'] != digest(prior/'transfer-protocol.json')
            or frozen['developmentProtocolSha256'] != digest(prior/'development-protocol.json')
            or report['inferenceLockSha256'] != digest(prior/'inference-lock.json')
            or report['recognitionSha256'] != digest(prior/'recognition.json')):
        raise ValueError('Retained evidence chain drift')
    if digest(retained/SOURCE) != labels['sourceSha256'] or labels['sourceSha256'] != frozen['sourceSha256']:
        raise ValueError('Retained source binding drift')
    if labels['completeHeadCensus'] is not True or labels['windows'] != report['completeWindows']:
        raise ValueError('Require unchanged complete source windows')
    if report['sourceHeadCount'] != len(labels['rows']):
        raise ValueError('Retained census count drift')
    for name, expected in receipt['artifactsSha256'].items():
        if digest(retained/name) != expected:
            raise ValueError('Retained recognition artifact drift')
    # The frozen manifest itself must still be tied to its original source/code
    # protocol, not silently regenerated by a newer historical runner.
    manifest = load(prior/'population-manifest.json')
    if manifest['protocolSha256'] != digest(prior/'development-protocol.json'):
        raise ValueError('Retained population protocol drift')
    if development['sourceSha256'] != labels['sourceSha256']:
        raise ValueError('Retained development source drift')
    return labels, report, manifest


def fit_bank(retained, manifest, evaluation_sha):
    from PIL import Image
    rows = manifest['samples']
    training.validate(rows)
    if len(rows) != 373 or evaluation_sha in {r['sourceSha256'] for r in rows}:
        raise ValueError('Unexpected expanded population or evaluation source leakage')
    paths, _ = source_paths(retained)
    images = {}
    for sha, path in paths.items():
        if digest(path) != sha:
            raise ValueError('Exemplar source hash drift')
        with Image.open(path) as image:
            images[sha] = image.convert('L')
    fitting = [dict(r, pixels=training.prior.classifier.crop(
        images[r['sourceSha256']], r['x'], r['y'], r['interline'])) for r in rows]
    return training.fit(fitting)


def classify(image, proposals, bank):
    rows = []
    for row in proposals:
        try:
            pixels = training.prior.classifier.crop(image, row['x'], row['y'], row['interline'])
            result = training.predict(pixels, bank)
        except ValueError as error:
            if str(error) != 'Note crop outside source':
                raise
            result = {'prediction': None, 'selectivePrediction': None,
                      'reason': 'automatic-crop-outside-source'}
        rows.append(dict(row, **result))
    return rows


def summarize(targets, predictions):
    arms = {}
    for radius in evaluation.RECIPE['sensitivityRadii']:
        pairs = evaluation.match(targets, predictions, radius)
        # The inherited nativePredictions field is valid only for native nodes.
        summary = evaluation.summarize(targets, predictions, pairs)
        summary['candidatePredictions'] = summary.pop('nativePredictions')
        strata = {}
        for label in sorted({r['label'] for r in targets if r['label'] is not None}):
            ids = {r['id'] for r in targets if r['label'] == label}
            strata[label] = {'sourceHeads': len(ids),
                             'matched': sum(p['sourceId'] in ids for p in pairs)}
        arms[str(radius)] = {'summary': summary, 'sourceStrata': strata, 'pairs': pairs}
    return arms


def run(retained, out):
    from PIL import Image
    retained, out = Path(retained).resolve(), Path(out).resolve()
    if out == retained/PRIOR or (retained/PRIOR) in out.parents:
        raise ValueError('Never write inside the retained frozen study')
    before = protocol(retained)
    immutable(out/'protocol.json', before)
    if (out/'report.json').exists():
        if digest(out/'report.json') != load(out/'receipt.json')['reportSha256']:
            raise ValueError('Completed development report drift')
        return load(out/'report.json')
    labels, old, manifest = retained_evidence(retained)
    bank = fit_bank(retained, manifest, labels['sourceSha256'])
    native = [dict(r, **r['models']['expanded']) for r in old['automaticPredictions']]
    with Image.open(retained/SOURCE) as image:
        native_queries = [dict(r, interline=old['automaticStaffLattices'][r['staff']]['interline'])
                          for r in native]
        replay = classify(image, native_queries, bank)
        fields = ('prediction', 'selectivePrediction', 'relativeMargin', 'neighborId',
                  'neighborGroup', 'distance', 'scale', 'offset')
        if any(a.get(k) != b.get(k) for a, b in zip(native, replay) for k in fields):
            raise ValueError('Reconstructed expanded bank differs from archived native queries')
        detected = detector.propose(image, labels['windows'])
        proposals = classify(image, detected['proposals'], bank)
    square = [r for r in proposals if r['selectivePrediction'] == 'square/filled']
    fused, suppressed = detector.fuse(native, square)
    arms = {'native-archived': native, 'image-only-all-cores': proposals,
            'image-only-selective-squares': square, 'native-plus-selective-squares': fused}
    result = {
        'protocolSha256': digest(out/'protocol.json'),
        'phase': before['phase'], 'source': 'SH2025/219',
        'sourceHeads': len(labels['rows']),
        'unchangedBankReplayQueries': len(replay),
        'sourceByClass': dict(Counter(r['label'] for r in labels['rows'])),
        'candidateStages': {'denseCoreProposals': len(proposals),
                            'geometricVetoes': len(detected['geometricVetoes']),
                            'selectiveSquares': len(square),
                            'classifierVetoes': len(proposals)-len(square),
                            'suppressedNearRetainedCenter': len(suppressed),
                            'addedToNative': len(fused)-len(native)},
        'arms': {name: summarize(labels['rows'], rows) for name, rows in arms.items()},
        'proposals': proposals, 'geometricVetoes': detected['geometricVetoes'],
        'suppressed': suppressed, 'staffLattices': detected['staffLattices'],
        'primaryArm': before['primaryArm'],
        'sourceCertified': False, 'safeToPromote': False, 'wholeScoresAccepted': 0,
        'freshSourceAccuracy': None, 'pitchRhythmAccuracy': None, 'measuredHumanMinutes': None,
    }
    if before != protocol(retained):
        raise ValueError('Inputs/code changed during development analysis')
    immutable(out/'report.json', result)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json')})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.retained_root, args.out)
    print(json.dumps({'phase': report['phase'], 'stages': report['candidateStages'],
                      'arms': {k: v['0.5']['summary'] for k, v in report['arms'].items()}}, indent=2))
