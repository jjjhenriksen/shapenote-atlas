from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_deterministic_imagegen_replacements.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeterministicImagegenReplacementTests(unittest.TestCase):
    def run_fixture(self, source_bytes: bytes = b"fixture-source") -> tuple[subprocess.CompletedProcess[str], Path]:
        temp = Path(tempfile.mkdtemp(prefix="deterministic-imagegen-test-"))
        source = temp / "source.jpg"
        if source_bytes == b"fixture-source":
            Image.new("RGB", (2, 3), (255, 255, 255)).save(source, format="JPEG", quality=95)
        else:
            source.write_bytes(source_bytes)
        source_hash = digest(source)
        batch_dir = temp / "work/transcription-images/working/imagegen-batches/batch-a"
        batch_dir.mkdir(parents=True)
        (batch_dir / "test-imagegen-v1.png").write_bytes(b"fixture-imagegen")
        (batch_dir / "test-imagegen-v1.png.audit.json").write_text(
            json.dumps({"status": "rejected-for-notation"}), encoding="utf-8"
        )
        source_manifest = temp / "source-manifest.json"
        source_manifest.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "songNo": "test",
                            "title": "Fixture",
                            "localPath": "source.jpg",
                            "sha256": source_hash,
                            "immutable": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        batch_manifest = temp / "batch.json"
        batch_manifest.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "artifactId": "batch-a/test",
                            "queueId": "sh2025/test",
                            "songNo": "test",
                            "source": {"path": "source.jpg", "manifestSha256": source_hash, "immutable": True},
                            "working": {"path": "work/transcription-images/working/imagegen-batches/batch-a/test-imagegen-v1.png"},
                            "audit": {"path": "old.audit.json", "present": True, "status": "rejected-for-notation"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        pilot_manifest = temp / "pilot.json"
        pilot_manifest.write_text(json.dumps({"records": []}), encoding="utf-8")
        output_root = temp / "deterministic"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(temp),
                "--batch-manifest",
                str(batch_manifest),
                "--pilot-manifest",
                str(pilot_manifest),
                "--source-manifest",
                str(source_manifest),
                "--batch-root",
                str(batch_dir.parent),
                "--pilot-root",
                str(temp / "work/transcription-images/working/imagegen-pilot"),
                "--output-root",
                str(output_root),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output_root

    def test_copy_is_byte_identical_and_fail_closed(self) -> None:
        result, output_root = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
        record = manifest["records"][0]
        output = output_root / Path(record["output"]["path"]).name
        self.assertTrue(output.is_file())
        self.assertEqual(record["source"]["sha256"], record["output"]["sha256"])
        self.assertEqual(record["source"]["dimensions"], record["output"]["dimensions"])
        self.assertTrue(record["review"]["failClosed"])
        self.assertFalse(record["review"]["automaticOmrAllowed"])
        self.assertFalse(record["review"]["safeToPromote"])

    def test_existing_conflicting_output_is_not_overwritten(self) -> None:
        result, output_root = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = next(output_root.glob("*-source-copy.jpg"))
        output.write_bytes(b"user-owned-conflict")
        second = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(output_root.parent),
                "--batch-manifest",
                str(output_root.parent / "batch.json"),
                "--pilot-manifest",
                str(output_root.parent / "pilot.json"),
                "--source-manifest",
                str(output_root.parent / "source-manifest.json"),
                "--batch-root",
                str(output_root.parent / "work/transcription-images/working/imagegen-batches"),
                "--pilot-root",
                str(output_root.parent / "work/transcription-images/working/imagegen-pilot"),
                "--output-root",
                str(output_root),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(output.read_bytes(), b"user-owned-conflict")


if __name__ == "__main__":
    unittest.main()
