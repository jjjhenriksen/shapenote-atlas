from __future__ import annotations

import sys
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reconcile_449_lovely_social_band_source_audit as lovely  # noqa: E402
import reconcile_520_ata_source_audit as ata  # noqa: E402
import agent_03_449_520_receipt as receipt  # noqa: E402


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return [item for item in (parent or []) if local(item.tag) == name]


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    return next(iter(children(parent, name)), None)


def text(parent: ET.Element | None, name: str) -> str:
    node = first(parent, name)
    return (node.text or "").strip() if node is not None else ""


def xml_bytes(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        name = next(item for item in archive.namelist() if item.endswith(".xml") and not item.startswith("META-INF/"))
        return archive.read(name)


def event_signature(root: ET.Element) -> list[tuple[str, str, str, str, str]]:
    result = []
    for part in children(root, "part"):
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    pitch_value = ":".join((text(pitch, "step"), text(pitch, "alter") or "0", text(pitch, "octave")))
                result.append((part.attrib.get("id", ""), measure.attrib.get("number", ""), pitch_value, text(note, "duration"), text(note, "voice")))
    return result


class SourceCorrectionTests(unittest.TestCase):
    def test_receipt_is_bounded_to_assigned_records(self):
        value = receipt.build_receipt()
        self.assertEqual(value["scope"], ["sh2025/449", "sh2025/520"])
        self.assertTrue(value["allRecordsBlocked"])
        self.assertFalse(value["otherRecordsTouched"])
        self.assertFalse(value["sharedLedgersRewritten"])
        self.assertTrue(all(item["draftFileSha256Verified"] for item in value["records"]))

    def test_lovely_correction_is_source_metadata_only_and_fail_closed(self):
        source = ROOT / "work/omr/source-shape-review-drafts/2025/449-source-shape-review.mxl"
        before = ET.fromstring(xml_bytes(source))
        after = ET.fromstring(lovely.update_xml(xml_bytes(source)))
        self.assertEqual(event_signature(before), event_signature(after))
        self.assertEqual(text(first(after, "work"), "work-title"), "Lovely Social Band")
        self.assertEqual(sum(1 for node in after.iter() if local(node.tag) == "notehead"), 0)
        for part in children(after, "part"):
            measure = children(part, "measure")[0]
            attributes = first(measure, "attributes")
            self.assertEqual(text(first(attributes, "key"), "fifths"), "-1")
            self.assertEqual(text(first(attributes, "key"), "mode"), "major")
            self.assertEqual(text(first(attributes, "time"), "beats"), "6")
            final = children(part, "measure")[-1]
            terminal = [bar for bar in children(final, "barline") if bar.attrib.get("location") == "right"]
            self.assertEqual(text(terminal[0], "bar-style"), "light-heavy")

    def test_ata_correction_preserves_events_and_encodes_terminal_bars(self):
        source = ROOT / "work/omr/520-ata/source.mxl"
        before = ET.fromstring(xml_bytes(source))
        after = ET.fromstring(ata.update_xml(xml_bytes(source), ata.sha256(ata.SOURCE_IMAGE), ata.sha256(source)))
        self.assertEqual(event_signature(before), event_signature(after))
        self.assertEqual(text(first(after, "work"), "work-title"), "Ata")
        self.assertEqual(sum(1 for node in after.iter() if local(node.tag) == "notehead"), 0)
        for part in children(after, "part"):
            measure = children(part, "measure")[0]
            attributes = first(measure, "attributes")
            self.assertEqual(text(first(attributes, "key"), "fifths"), "-2")
            self.assertEqual(text(first(attributes, "key"), "mode"), "major")
            self.assertEqual(text(first(attributes, "time"), "beats"), "4")
            final = children(part, "measure")[-1]
            terminal = [bar for bar in children(final, "barline") if bar.attrib.get("location") == "right"]
            self.assertEqual(text(terminal[0], "bar-style"), "light-heavy")


if __name__ == "__main__":
    unittest.main()
