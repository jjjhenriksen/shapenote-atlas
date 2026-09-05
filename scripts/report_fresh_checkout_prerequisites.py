#!/usr/bin/env python3
"""Report retained-source prerequisites present in this checkout.

This is an evidence report, not a replacement for fidelity validation. A
missing retained-source path is an environment prerequisite for the
corresponding validator; the validator must still run and fail closed when
that prerequisite is absent. The inventory covers the known tracked fidelity
validators and current public ledgers, not every possible data-lane input.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

FIXED = (
    ("validator-manifest", "work/source-transcriptions/2025/clean-source-candidates.json", "validate_data,validate_source_candidates,check_source_health"),
    ("validator-manifest", "work/omr/review-shape-drafts/2025/manifest.json", "validate_shape_review_drafts"),
    ("validator-manifest", "work/omr/source-shape-review-drafts/2025/manifest.json", "validate_source_shape_review_drafts"),
    ("validator-manifest", "work/transcription-images/manifest.json", "validate_transcription_images"),
    ("validator-run-ledger", "work/omr/cleaned-v1-run.json", "validate_transcription_images"),
    ("validator-run-ledger", "work/omr/cleaned-normalized-v2-run.json", "validate_transcription_images"),
)

GENERATED_OUTPUTS = (
    ("validator-output", "work/omr/draft-index.json", "audit_omr_drafts"),
)


def add_requirement(requirements: dict[str, dict[str, Any]], kind: str, path: str, consumer: str) -> None:
    item = requirements.setdefault(path, {"path": path, "kinds": set(), "consumers": set()})
    item["kinds"].add(kind)
    item["consumers"].add(consumer)


def load_public(name: str) -> Any:
    return json.loads((PUBLIC / name).read_text(encoding="utf-8"))


def collect_requirements() -> dict[str, dict[str, Any]]:
    requirements: dict[str, dict[str, Any]] = {}
    for kind, path, consumer in FIXED:
        add_requirement(requirements, kind, path, consumer)

    source_health = load_public("source-health.json")
    for record in source_health.get("records", []):
        for evidence in record.get("localEvidence", []):
            path = str(evidence.get("path", ""))
            if path:
                add_requirement(requirements, "source-health-local-evidence", path, "validate_source_health")

    image_queue = load_public("image-review-queue.json")
    for record in image_queue.get("records", []):
        original = record.get("original", {})
        if original.get("path"):
            add_requirement(requirements, "image-review-original", str(original["path"]), "validate_image_review_queue")
        for layer_name, layer in (record.get("workingLayers", {}) or {}).items():
            if layer.get("path"):
                add_requirement(requirements, f"image-review-{layer_name}", str(layer["path"]), "validate_image_review_queue")

    return requirements


def build_report() -> dict[str, Any]:
    requirements = collect_requirements()
    records = []
    for path in sorted(requirements):
        item = requirements[path]
        absolute = (ROOT / path).resolve()
        try:
            absolute.relative_to(ROOT.resolve())
            within_root = True
        except ValueError:
            within_root = False
        exists = within_root and absolute.is_file()
        records.append(
            {
                "path": path,
                "exists": exists,
                "kinds": sorted(item["kinds"]),
                "consumers": sorted(item["consumers"]),
            }
        )
    missing = [item for item in records if not item["exists"]]
    by_kind = Counter(kind for item in missing for kind in item["kinds"])
    generated_outputs = [
        {"path": path, "exists": (ROOT / path).is_file(), "consumers": [consumer]}
        for _, path, consumer in GENERATED_OUTPUTS
    ]
    return {
        "schemaVersion": 1,
        "kind": "fresh-checkout-retained-source-prerequisites",
        "projectRoot": str(ROOT),
        "policy": {
            "reportOnly": True,
            "missingMeansEnvironmentPrerequisite": True,
            "fidelityValidatorsRemainFailClosed": True,
            "noMissingPrerequisiteIsSilentlySkipped": True,
            "exhaustiveAcrossDataLanes": False,
        },
        "inventoryScope": "known tracked fidelity validators and current public source-health/image-review ledgers; coordinate with the data lane for any additional builder-specific inputs",
        "summary": {
            "requiredRetainedSourcePaths": len(records),
            "presentRetainedSourcePaths": len(records) - len(missing),
            "missingRetainedSourcePaths": len(missing),
            "missingByKind": dict(sorted(by_kind.items())),
            "generatedOutputs": len(generated_outputs),
            "missingGeneratedOutputs": sum(not item["exists"] for item in generated_outputs),
        },
        "missing": missing,
        "requirements": records,
        "generatedOutputs": generated_outputs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, help="Optional report path")
    args = parser.parse_args()
    report = build_report()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
