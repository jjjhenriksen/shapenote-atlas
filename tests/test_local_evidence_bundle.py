"""Safety and round-trip tests for the local retained-evidence bundle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "local_evidence_bundle.py"
SPEC = importlib.util.spec_from_file_location("local_evidence_bundle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalEvidenceBundleTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        holder = tempfile.TemporaryDirectory(dir=ROOT)
        root = Path(holder.name) / "source"
        root.mkdir()
        files = {
            "work/retained/a.mxl": b"exact-a",
            "work/retained/nested/b.jpg": b"exact-b",
        }
        records = []
        for relative, contents in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
            records.append(
                {
                    "path": relative,
                    "artifactClasses": ["immutable-retained-source"],
                    "status": "present",
                    "bytes": len(contents),
                    "sha256": hashlib.sha256(contents).hexdigest(),
                    "expectedSha256": [],
                    "expectedBytes": [],
                    "sourceUrls": [f"https://example.test/{Path(relative).name}"],
                    "consumers": ["scripts/validate_source_health.py"],
                    "gates": ["source-health"],
                    "references": ["fixture"],
                    "tracked": False,
                    "immutable": True,
                    "derived": False,
                    "acquisitionRequirement": "restore exact bytes",
                }
            )
        manifest = root / "dependency-manifest.json"
        manifest.write_text(json.dumps({"schemaVersion": 1, "records": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return holder, root, manifest

    def test_round_trip_and_idempotent_restore(self) -> None:
        holder, root, manifest = self.fixture()
        self.addCleanup(holder.cleanup)
        bundle = Path(holder.name) / "bundle"
        self.assertEqual(MODULE.export_bundle(root, manifest, bundle)["files"], 2)
        verified = MODULE.validate_bundle(bundle)
        self.assertEqual(verified["files"], 2)
        destination = Path(holder.name) / "fresh-checkout"
        restored = MODULE.restore_bundle(bundle, destination, root)
        self.assertEqual(restored["restored"], 2)
        self.assertEqual(restored["alreadyPresent"], 0)
        again = MODULE.restore_bundle(bundle, destination, root)
        self.assertEqual(again["restored"], 0)
        self.assertEqual(again["alreadyPresent"], 2)
        self.assertEqual((destination / "work/retained/a.mxl").read_bytes(), b"exact-a")
        self.assertEqual((destination / "work/retained/nested/b.jpg").read_bytes(), b"exact-b")
        bundle_payload = json.loads((bundle / "bundle-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(bundle_payload["selectionSummary"]["completeForAllManifestDependencies"])
        self.assertEqual(bundle_payload["selectionSummary"]["excludedTracked"], 0)

    def test_missing_manifest_dependency_is_excluded_without_completeness_claim(self) -> None:
        manifest = {
            "records": [
                {"path": "work/missing.mxl", "tracked": False, "status": "missing"},
                {"path": "public/tracked.json", "tracked": True, "status": "present"},
            ]
        }
        selected = MODULE.selected_records(manifest)
        summary = MODULE.selection_summary(manifest, selected)
        self.assertEqual(selected, [])
        self.assertEqual(summary["excludedMissingOrUnavailable"], 1)
        self.assertFalse(summary["completeForSelectedPresentUntracked"])
        self.assertFalse(summary["completeForAllManifestDependencies"])

    def test_tampered_bundle_is_rejected(self) -> None:
        holder, root, manifest = self.fixture()
        self.addCleanup(holder.cleanup)
        bundle = Path(holder.name) / "bundle"
        MODULE.export_bundle(root, manifest, bundle)
        (bundle / "files/work/retained/a.mxl").write_bytes(b"tampered")
        with self.assertRaises(MODULE.BundleError):
            MODULE.validate_bundle(bundle)

    def test_missing_source_and_conflicting_destination_are_fail_closed(self) -> None:
        holder, root, manifest = self.fixture()
        self.addCleanup(holder.cleanup)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["records"][0]["path"] = "work/retained/missing.mxl"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(MODULE.BundleError):
            MODULE.export_bundle(root, manifest, Path(holder.name) / "missing-bundle")

        holder2, root2, manifest2 = self.fixture()
        self.addCleanup(holder2.cleanup)
        bundle = Path(holder2.name) / "bundle"
        MODULE.export_bundle(root2, manifest2, bundle)
        destination = Path(holder2.name) / "destination"
        destination.mkdir()
        (destination / "work/retained").mkdir(parents=True)
        (destination / "work/retained/nested").mkdir()
        (destination / "work/retained/nested/b.jpg").write_bytes(b"conflict")
        with self.assertRaises(MODULE.BundleError):
            MODULE.restore_bundle(bundle, destination, root2)
        self.assertFalse((destination / "work/retained/a.mxl").exists(), "preflight must prevent partial restore")

    def test_traversal_absolute_and_symlink_escape_are_rejected(self) -> None:
        holder, root, manifest = self.fixture()
        self.addCleanup(holder.cleanup)
        bundle = Path(holder.name) / "bundle"
        MODULE.export_bundle(root, manifest, bundle)

        for unsafe_path in ("../escape", "/absolute"):
            bundle_payload = json.loads((bundle / "bundle-manifest.json").read_text(encoding="utf-8"))
            bundle_payload["files"][0]["path"] = unsafe_path
            (bundle / "bundle-manifest.json").write_text(json.dumps(bundle_payload), encoding="utf-8")
            with self.assertRaises(MODULE.BundleError):
                MODULE.validate_bundle(bundle)
            shutil.rmtree(bundle)
            MODULE.export_bundle(root, manifest, bundle)

        bundle_manifest_real = bundle / "bundle-manifest-real.json"
        (bundle / "bundle-manifest.json").rename(bundle_manifest_real)
        (bundle / "bundle-manifest.json").symlink_to(bundle_manifest_real.name)
        with self.assertRaises(MODULE.BundleError):
            MODULE.validate_bundle(bundle)

        shutil.rmtree(bundle)
        MODULE.export_bundle(root, manifest, bundle)
        outside = Path(holder.name) / "outside"
        outside.mkdir()
        destination_link = Path(holder.name) / "destination-link"
        destination_link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(MODULE.BundleError):
            MODULE.restore_bundle(bundle, destination_link, root)

        destination_base = Path(holder.name) / "destination-base"
        destination_base.mkdir()
        outside_link = Path(holder.name) / "outside-link"
        outside_link.mkdir()
        (destination_base / "nested-link").symlink_to(outside_link, target_is_directory=True)
        nested_destination = destination_base / "nested-link" / "checkout"
        with self.assertRaises(MODULE.BundleError):
            MODULE.restore_bundle(bundle, nested_destination, root)
        (destination_base / "dangling-link").symlink_to(Path(holder.name) / "does-not-exist", target_is_directory=True)
        dangling_destination = destination_base / "dangling-link" / "checkout"
        with self.assertRaises(MODULE.BundleError):
            MODULE.restore_bundle(bundle, dangling_destination, root)
        self.assertFalse((outside_link / "checkout").exists())

        shutil.rmtree(bundle)
        MODULE.export_bundle(root, manifest, bundle)
        (bundle / "files/work/retained/a.mxl").unlink()
        (bundle / "files/work/retained/a.mxl").symlink_to(outside / "not-a-source")
        with self.assertRaises(MODULE.BundleError):
            MODULE.validate_bundle(bundle)

    def test_restore_never_targets_the_source_checkout(self) -> None:
        holder, root, manifest = self.fixture()
        self.addCleanup(holder.cleanup)
        bundle = Path(holder.name) / "bundle"
        MODULE.export_bundle(root, manifest, bundle)
        with self.assertRaises(MODULE.BundleError):
            MODULE.restore_bundle(bundle, root, root)


if __name__ == "__main__":
    unittest.main()
