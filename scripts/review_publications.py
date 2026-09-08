#!/usr/bin/env python3
"""Publish pinned, correctable review drafts without granting canonical status.

Run directly for a targeted update; build_data also runs this after regeneration.
The manifest, not candidate filenames or historical safeToPromote flags, authorizes
review publication. Original candidate bytes and all other corpus rows are retained.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/review-publications.json"


def score_xml(payload: bytes) -> ET.Element:
    """Read the same score member used by the semantic parser, without rewriting it."""
    if zipfile.is_zipfile(io.BytesIO(payload)):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            name = next(name for name in archive.namelist()
                        if name.endswith('.xml') and 'container' not in name)
            payload = archive.read(name)
    return ET.fromstring(payload)


def preserved_notation(element: ET.Element) -> tuple:
    # These candidates document only lyric, derived-shape and mode additions.
    # Compare all remaining part semantics, including pitches/timing/navigation.
    return (element.tag, tuple(sorted(element.attrib.items())),
            (element.text or '').strip(), tuple(preserved_notation(child)
            for child in element if child.tag not in ('lyric', 'notehead', 'mode')))


def write_changed(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() == payload:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replace only this generated file, never a source candidate or repository index.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def publish(root: Path = ROOT, public: Path | None = None, manifest: Path | None = None) -> list[str]:
    from build_data import (parse_score, prepare_score_for_playback,
                            build_draft_playback_validation, _add_transposition_capability)
    public = public or root / "public"
    manifest = manifest or root / "scripts/review-publications.json"
    entries = json.loads(manifest.read_text())["publications"]
    documents = {name: json.loads((public / f"{name}.json").read_text())
                 for name in ("corpus", "source-coverage", "transcription-queue")}
    corpus = documents["corpus"]
    songs = {song["id"]: song for song in corpus["songs"]}
    published = []
    pending_assets = {}
    for entry in entries:
        song = songs[entry["songId"]]
        book = entry["bookId"]
        if book not in song["books"]:
            raise ValueError(f"Publication book mismatch: {entry['songId']}")
        stem = entry["slug"] + "-" + entry["version"]
        urls = {}
        inputs = {}
        fields = [("musicXml", "musicXmlUrl"), ("source", "sourceUrl"), ("evidence", "evidenceUrl")]
        if "originalMusicXml" in entry:
            fields.append(("originalMusicXml", "originalMusicXmlUrl"))
        for field, url_field in fields:
            spec = entry[field]
            path = root / spec["path"]
            name = stem + "-" + field + path.suffix
            packaged = root / "public" / "review-publications" / name
            retained = path if path.exists() else packaged if packaged.exists() else public / "review-publications" / name
            payload = retained.read_bytes()
            inputs[field] = payload
            if hashlib.sha256(payload).hexdigest() != spec["sha256"]:
                raise ValueError(f"Pinned publication input changed: {path}")
            name = stem + "-" + field + path.suffix
            urls[url_field] = "/review-publications/" + name
            pending_assets[public / "review-publications" / name] = payload
        metadata = {**urls, "version": entry["version"], "completeness": entry["completeness"],
                    "limitations": entry["limitations"]}
        xml = inputs["musicXml"]
        if "originalMusicXml" in inputs:
            original = score_xml(inputs["originalMusicXml"])
            candidate = score_xml(xml)
            if ([preserved_notation(part) for part in original.findall('part')] !=
                    [preserved_notation(part) for part in candidate.findall('part')]):
                raise ValueError(f"Source notation changed outside documented corrections: {entry['songId']}")
        with tempfile.TemporaryDirectory() as temporary:
            mxl = Path(temporary) / "score.mxl"
            if zipfile.is_zipfile(io.BytesIO(xml)):
                mxl.write_bytes(xml)
            else:
                with zipfile.ZipFile(mxl, "w") as archive:
                    archive.writestr("score.xml", xml)
            score = parse_score(urls["musicXmlUrl"], mxl)
            if not score:
                raise ValueError(f"No playable score: {entry['songId']}")
            # The semantic parser records the temporary wrapper; expose stable evidence instead.
            score = json.loads(json.dumps(score).replace(str(mxl), entry["musicXml"]["path"]))
        if build_draft_playback_validation(stem, score, {}):
            raise ValueError(f"Invalid event durations: {entry['songId']}")
        score["reviewPublication"] = metadata
        score["availability"] = copy.deepcopy(score.get("semanticContract", {}).get("availability", {}))
        score["keyEvidence"] = {"status": "unknown", "source": "Review draft; tonal interpretation has not been verified"}
        score["keySignature"] = ""
        score["provenance"] = {
            "kind": "omr-draft", "label": "Published review draft", "reviewRequired": True,
            "sourceEdition": book, "sourceRecordKey": song["songNo"],
            "sourceArtifact": entry["musicXml"]["path"], "sourceSha256": entry["musicXml"]["sha256"],
            "sourceKeyVerified": False, "transcriptionMethod": entry.get("transcriptionMethod", "manual"),
        }
        prepare_score_for_playback(score)
        _add_transposition_capability(score)
        ref = "/draft-scores/" + stem + ".json"
        pending_assets[public / ref.lstrip("/")] = json_bytes(score)
        preview = copy.deepcopy(score)
        preview["scoreRef"] = ref
        preview["parts"] = [{"name": part["name"], "events": []} for part in score["parts"]]
        song.setdefault("draftScoreByBook", {})[book] = preview
        coverage_patch = {"draftScoreAvailable": True, "draftScoreRef": ref,
                          "draftScoreStatus": "needs-human-review", "reviewPublication": metadata,
                          "nextAction": "review-and-correct-published-draft"}
        song.setdefault("sourceCoverageByBook", {}).setdefault(book, {}).update(coverage_patch)
        if len(song["books"]) == 1:
            song.setdefault("sourceCoverage", {}).update(coverage_patch)
        for name in ("source-coverage", "transcription-queue"):
            for record in documents[name]["records"]:
                if record.get("songId") == entry["songId"] and record.get("bookId") == book:
                    record.update(copy.deepcopy(coverage_patch))
                    if name == "transcription-queue":
                        disposition = {"state": "needs-human-review", "role": "published-draft-correction",
                                       "humanReviewRequired": True, "reviewAvailable": True, "safeToPromote": False,
                                       "reason": "Playable review draft published; source fidelity is not yet certified.",
                                       "autonomousDecision": "published-for-correction"}
                        record.update({"disposition": disposition, "humanReviewRequired": True,
                                       "reviewAvailable": True, "safeToPromote": False})
        published.append(entry["songId"])
    # Recalculate only draft-sensitive counts; never inflate verified-score totals.
    for book in {entry["bookId"] for entry in entries}:
        book_songs = [song for song in corpus["songs"] if book in song.get("books", [])]
        coverage = corpus["coverage"]["byBook"][book]
        coverage["transposableDraftRecords"] = sum(bool(song.get("draftScoreByBook", {}).get(book, {}).get("transposition", {}).get("available")) for song in book_songs)
        coverage["transposableRecords"] = sum(any(song.get(field, {}).get(book, {}).get("transposition", {}).get("available") for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook")) for song in book_songs)
        coverage["keyUnknownStructuredRecords"] = sum(
            any(song.get(field, {}).get(book, {}).get("transposition", {}).get("hasPitchedEvents") for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"))
            and not any(song.get(field, {}).get(book, {}).get("transposition", {}).get("available") for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"))
            for song in book_songs)
    # All inputs and scores pass validation before any publication is written.
    for path, payload in pending_assets.items():
        write_changed(path, payload)
    for name, document in documents.items():
        write_changed(public / f"{name}.json", json_bytes(document))
    return published


if __name__ == "__main__":
    print("Published review drafts: " + ", ".join(publish()))
