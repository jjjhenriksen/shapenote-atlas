#!/usr/bin/env python3
"""Build a compact, provenance-preserving browser bundle from source data.

The existing corpus dashboard remains the metadata source of truth. Complete
MusicXML is admitted only from an exact local cache or an exact mapping recorded
by ``fetch_shapenote_scores.py``; records without one stay visibly unscored.
"""

from __future__ import annotations

import csv
import copy
import hashlib
import json
import re
import sys
from urllib.parse import unquote, urlparse
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from review_dispositions import transcription_disposition


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path("/Users/jacquelinehenriksen/sh-corpus-scripts")
SOURCE_DATA = SOURCE_ROOT / "dashboard/data.js"
SOURCE_METADATA = SOURCE_ROOT / "rag_web_metadata.csv"
EDITION_CHANGES = SOURCE_ROOT / "changed_across_editions.csv"
CACHE_ROOT = SOURCE_ROOT / ".cache/rag_metadata"
OUTPUT = PROJECT_ROOT / "public/corpus.json"
TRANSCRIPTION_QUEUE_OUTPUT = PROJECT_ROOT / "public/transcription-queue.json"
SCORES_OUTPUT = PROJECT_ROOT / "public/scores"
DRAFT_SCORES_OUTPUT = PROJECT_ROOT / "public/draft-scores"
REMOTE_MANIFEST = PROJECT_ROOT / "public/shapenote-score-manifest.json"
SOURCE_IMAGE_MANIFEST = PROJECT_ROOT / "public/source-image-manifest.json"
SOURCE_METADATA_OBSERVATIONS = PROJECT_ROOT / "public/source-metadata-observations.json"
SHAPENOTE_2025_SCORE_AUDIT = PROJECT_ROOT / "public/shapenote-2025-score-audit.json"
EDITION_ADDITIONS_2025 = PROJECT_ROOT / "public/edition-2025-additions.json"
TRANSCRIPTION_ROOT = PROJECT_ROOT / "work" / "source-transcriptions"
OMR_ROOT = PROJECT_ROOT / "work" / "omr"
SOURCE_RECORDINGS = TRANSCRIPTION_ROOT / "2025" / "recording-index.json"
SOURCE_DEBUT_RECORDINGS = TRANSCRIPTION_ROOT / "2025" / "debut-recording-index.json"
SOURCE_CLEAN_CANDIDATES = TRANSCRIPTION_ROOT / "2025" / "clean-source-candidates.json"
SOURCE_CLEAN_OMR_RUN = OMR_ROOT / "clean-source-omr-run.json"
DRAFT_INDEX = PROJECT_ROOT / "work" / "omr" / "draft-index.json"
METADATA_KEY_ALIASES = {
    # The corpus keeps edition-specific suffixes on these pages while the
    # metadata export uses the neighboring Fasola index key. These are
    # explicit, source-audited aliases—not fuzzy title matching.
    "sh1991": {"313": "313b", "445b": "445", "503b": "503"},
}
# The source index uses a few historical suffixes that are not present on the
# current corpus records. These are explicit same-book/title mappings, not
# fuzzy matching. Keep them separate from edition metadata aliases so a score
# can be recovered without changing a source record's displayed page key.
REMOTE_SCORE_ALIASES = {
    "shcooper2012": {
        "59t": "59",
        "207t": "393b",
        "207b": "207",
        "393": "393t",
        "488": "488t",
        "519": "519b",
    },
    "southernharmony": {
        "17": "17t",
        "25": "25t",
        "31": "31t",
        "39": "39t",
        "53": "53t",
        "72": "72t",
        "181": "181t",
        "312": "312t",
        "333": "333t",
    },
}
EXACT_SCORE_URLS = {
    # The public 2025 catalog places both Lisbons in its 2025 section, but
    # they live on different pages and have different composers.
    "https://shapenote.net/musicxml/X-Lis.mxl",
    "https://shapenote.net/musicxml/SH25-LISBON-Chandler.mxl",
}
# The local metadata export predates the 2025 index and carries a copied
# 1991 URL for these two pages. Keep that legacy evidence, but make the
# edition-specific source record canonical in the generated atlas.
EDITION_SOURCE_OVERRIDES = {
    ("sh2025", "106"): {
        "sourceUrl": "https://fasola.org/indexes/2025/?p=106",
        "sourceUrls": ["https://fasola.org/indexes/2025/?p=106"],
    },
    ("sh2025", "414b"): {
        "sourceUrl": "https://fasola.org/indexes/2025/?p=414b",
        "sourceUrls": ["https://fasola.org/indexes/2025/?p=414b"],
    },
    ("sh2025", "467"): {
        "sourceUrl": "https://fasola.org/indexes/2025/?p=467",
        "sourceUrls": [
            "https://fasola.org/indexes/2025/?p=467",
            "https://shapenote.net/musicxml/X-Lis.mxl",
        ],
    },
    ("sh2025", "575"): {
        "sourceUrl": "https://fasola.org/indexes/2025/?p=575",
        "sourceUrls": [
            "https://fasola.org/indexes/2025/?p=575",
            "https://shapenote.net/musicxml/SH25-LISBON-Chandler.mxl",
        ],
    },
}

# Directly inspected current-edition source-page evidence. These overrides are
# intentionally narrow and carry the immutable remote witness identity; they
# supersede a cross-edition candidate only when the current edition scan
# visibly prints the key and mode.
DIRECT_SOURCE_KEY_OVERRIDES = {
    ("sh2025", "27t"): {
        "key": "F minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/027t-Bethel/27t.jpg",
        "sourceImageSha256": "a05657341050fb78088b8b5c39f2e5b5ff4750dc9cc10b9317436ba16c41bf09",
        "observation": "Page header visibly prints F Minor.",
    },
    ("sh2025", "37t"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/037t-Ester/37t.jpg",
        "sourceImageSha256": "8193878858fb7cc8eff67bb4dce49e53a27e75873907f63cc6e7c35592fb81df",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "78"): {
        "key": "A major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/078-Stafford/78.jpg",
        "sourceImageSha256": "49c092e70c61af6614e2cc2b31176f5b5ecfde0d042706d1913a9f56f49b9172",
        "observation": "Page header visibly prints A Major.",
    },
    ("sh2025", "135"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/135-Olney/135.jpg",
        "sourceImageSha256": "cf5ed9110af2871ec1d09c2486944af42ee5722f9646d50ed08833c4f666278d",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "145t"): {
        "key": "G major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/145t-Warrenton/145t.jpg",
        "sourceImageSha256": "01e7b9c538271663d02cc6c1ed2af0c461cf876b8a5c6ee34813bc84d188b50e",
        "observation": "Page header visibly prints G Major.",
    },
    ("sh2025", "154"): {
        "key": "Eb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/154-Rest-for-the-Weary/154.jpg",
        "sourceImageSha256": "2f1f4061036231f712a2062dcb74e1fbbe55a52e00a1941420bae07deca9df9b",
        "observation": "Page header visibly prints Eb Major.",
    },
    ("sh2025", "176t"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/176t-Ragan/176t.jpg",
        "sourceImageSha256": "2a08b7d52cd336824271886b162d9795ba5310f95a1f2193a741a2f92272f0b1",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "178t"): {
        "key": "Eb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/178t-Africa/178t.jpg",
        "sourceImageSha256": "900867f392b8792d3de62bb8f10f1ac7032e90b38292883a2a1d8f5f6a018d3f",
        "observation": "Page header visibly prints Eb Major.",
    },
    ("sh2025", "211"): {
        "key": "E minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/211-Whitestown/211.jpg",
        "sourceImageSha256": "616343c9a3433703e7a983848f6031be6b853d898ae4904e4ae9fb69e3494b6d",
        "observation": "Page header visibly prints E Minor.",
    },
    ("sh2025", "274t"): {
        "key": "F# minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/274t-The-Golden-Harp/274t.jpg",
        "sourceImageSha256": "0bf1a05e573b0633e74b8640a0daad860cff2684366029ee061b18d1a4fe66b6",
        "observation": "Page header visibly prints F# Minor.",
    },
    ("sh2025", "278b"): {
        "key": "G minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/278b-Traveling-Pilgrim/278b.jpg",
        "sourceImageSha256": "1075c7d10fa7b894038cbb0d4f60bdd647b26157eb3a8a7bb5d51eca3507c380",
        "observation": "Page header visibly prints G Minor.",
    },
    ("sh2025", "282"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/282-Im-Going-Home/282.jpg",
        "sourceImageSha256": "6b0a3478d5e5a7b4fa3f0fb05b13f65bdf08d813f7139662599bea1e34eac45f",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "330t"): {
        "key": "E minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/330t-Fellowship/330t.jpg",
        "sourceImageSha256": "ace8086e523ad8169c2208fe477294600fff5288130bfc983878ca106c60bf13",
        "observation": "Page header visibly prints E Minor.",
    },
    ("sh2025", "333"): {
        "key": "A major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/333-Family-Circle/333.jpg",
        "sourceImageSha256": "023cf1db764ecd45edda624c80d570d46c99ae1555fc633005bf53fa81c6530d",
        "observation": "Page header visibly prints A Major.",
    },
    ("sh2025", "347b"): {
        "key": "Bb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/347b-Humility/347b.jpg",
        "sourceImageSha256": "add1bfd7f38cff17d3db575a7bd2863c3e87ddc4ddbbdd2aa25aea60eebe0c8b",
        "observation": "Page header visibly prints Bb Major.",
    },
    ("sh2025", "347t"): {
        "key": "Bb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/347t-Christians-Farewell/347t.jpg",
        "sourceImageSha256": "e5d32892df97875fed9a9df5a6e0bb0ceec63d44a9eae4595e082f1718677a8d",
        "observation": "Page header visibly prints Bb Major.",
    },
    ("sh2025", "360"): {
        "key": "E minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/360-The-Royal-Band/360-The-Royal-Band.jpg",
        "sourceImageSha256": "75f248a5e7fcd0412e31722fa04c0bb217b81f290e6bd84da0c4c3b8fc73096b",
        "observation": "Page header visibly prints E Minor.",
    },
    ("sh2025", "364"): {
        "key": "E major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/364-Southwell/364.jpg",
        "sourceImageSha256": "a6bb14e08d401db05f3a1c0c0cb2e915626cd7223f5c52b9a7211aaa9ab0e869",
        "observation": "Page header visibly prints E Major.",
    },
    ("sh2025", "423t"): {
        "key": "F# minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/423t-Grantville/423t.jpg",
        "sourceImageSha256": "3e8ab71e2ae6657f5757305d6ae1ddf3fd57d1369e463a9242d1c8620910f069",
        "observation": "Page header visibly prints F# Minor.",
    },
    ("sh2025", "452b"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/452b-Martin/452b.jpg",
        "sourceImageSha256": "450fe59f0150ca75ba39db5994e2328ca4d3ffdb82a3056648e30dc556db40b7",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "497t"): {
        "key": "A major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/497t-Natick/497t.jpg",
        "sourceImageSha256": "87089c4e18c50491f5a53ad88cdc64e17841f948da76f7fa8e456fce23dcaeb2",
        "observation": "Page header visibly prints A Major.",
    },
    ("sh2025", "499b"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/499b-At-Rest/499b.jpg",
        "sourceImageSha256": "5c79b58ef0bc44c9141ba8cf1f8f4092eb0b697047a471df05b0790490b8d3fe",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "501b"): {
        "key": "G major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/501b-O-Leary/501b.jpg",
        "sourceImageSha256": "8a46883392a311cf3f0c2bd60405e91d6af565de09286a8b88c46046961f8809",
        "observation": "Page header visibly prints G Major.",
    },
    ("sh2025", "503"): {
        "key": "F major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/503-Lloyd/503.jpg",
        "sourceImageSha256": "cb4134eaad5e6be557533f3c94b87cdf9cfff31592c067d5e8413ead62bda249",
        "observation": "Page header visibly prints F Major.",
    },
    ("sh2025", "508"): {
        "key": "Eb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/508-Sermon-on-the-Mount/508.jpg",
        "sourceImageSha256": "00c79c07d7cbbce783da278204b8ea5772a43c2167f8dff66e6c3a037e772032",
        "observation": "Page header visibly prints Eb Major.",
    },
    ("sh2025", "77t"): {
        "key": "A minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/077t-The-Child-of-Grace/77t.jpg",
        "sourceImageSha256": "f884e0d491cbda5a8595e2531de17850c690ef74d3edd391cad69602bedde063",
        "observation": "Page header visibly prints A Minor.",
    },
    ("sh2025", "313b"): {
        "key": "A minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/313b-Cobb/313b-Cobb.jpg",
        "sourceImageSha256": "dae49ed2f3b60a64452b4f7650e524e910433066f2650670375f73181fa913b3",
        "observation": "Page header visibly prints A Minor.",
    },
    ("sh2025", "445"): {
        "key": "C major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/445-Passing-Away/445.jpg",
        "sourceImageSha256": "41c25d252f871a5e91ff8e31b536a35dd657d831dc131060bee5e6433604800b",
        "observation": "Page header visibly prints C Major.",
    },
    ("sh2025", "497b"): {
        "key": "A minor",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/497b-Supplication/497b.jpg",
        "sourceImageSha256": "b33ab77a853eb91ec99a53cbbd32d3f399296ea902ca1a367f4c72ec44da663d",
        "observation": "Page header visibly prints A Minor.",
    },
    ("sh2025", "565b"): {
        "key": "A major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/565b-The-Hill-of-Zion/565b.jpg",
        "sourceImageSha256": "5f54e8b7cd5a1082bcef7f64a4a3b93c149f8d228b0cb42d372f3769fef10359",
        "observation": "Fasola 2025 page 565b identifies The Hill of Zion; the scan header visibly prints A Major.",
    },
    ("sh2025", "565t"): {
        "key": "Bb major",
        "source": "direct current-edition source image inspection",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/565t-Hebron/565t.jpg",
        "sourceImageSha256": "377b9fed5cbd721fd427527d23bd64f00cce2357e0d9e62edca387c642c89985",
        "observation": "Fasola 2025 page 565t identifies Hebron; the scan header visibly prints Bb Major.",
    },
}

# The local Obsidian export was generated before the live 2025 index settled.
# Keep its superseded notes available in the generated bundle, while making
# the current index the displayed edition record. These entries are metadata
# only until an edition-specific structured score is verified.
CURRENT_2025_INDEX_ADDITIONS = {
    "414b": {
        "title": "Parting Friend",
        "textKey": "the time must come when we must part",
        "rawFirstLine": "The time must come when we must part,",
        "composer": "J. C. Graham",
        "lyricist": "The Sacred Harp",
        "meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
        "timeSignature": "4/4",
        "sourceUrl": "https://fasola.org/indexes/2025/?p=414b",
    },
    "414t": {
        "title": "Farewell Brethren",
        "textKey": "brethren i bid you all farewell",
        "rawFirstLine": "Brethren, I bid you all farewell,",
        "composer": "Jesse P. Karlsberg",
        "lyricist": "Winchester’s Collection",
        "meter": "Common Meter (8,6,8,6)",
        "timeSignature": "",
        "sourceUrl": "https://fasola.org/indexes/2025/?p=414t",
    },
    "484t": {
        "title": "Millbrook",
        "textKey": "how long thou faithful god shall i",
        "rawFirstLine": "How long, Thou faithful God, shall I",
        "composer": "Neely Bruce",
        "lyricist": "Charles Wesley",
        "meter": "Long Meter (8,8,8,8)",
        "timeSignature": "",
        "sourceUrl": "https://fasola.org/indexes/2025/?p=484t",
    },
}

# Explicit, source-audited cross-edition witnesses. These are deliberately
# narrow: a shared title or number is not enough to infer that two engravings
# are interchangeable. The resulting score remains a reference witness in the
# selected edition, never an exact 2025 score.
CROSS_EDITION_SCORE_REFERENCES = {
    ("sh2025", "414b"): ("sh1991", "414"),
    # The 2025 scan for Bishop is the same four-part setting as 1991 page
    # 420, but the current edition assigns it the distinct key 420b. Keep the
    # witness explicitly edition-labeled rather than treating it as exact
    # 2025 notation.
    ("sh2025", "420b"): ("sh1991", "420"),
}

EXPLICIT_EDITION_RECONCILIATIONS = {
    ("sh1991", "420"): {
        "books": ["sh1991", "sh2025"],
        "status": "same-setting-renumbered",
        "relationId": "sh-edition:420b",
        "relationType": "edition-pair",
        "records": {
            "sh1991": {
                "songNo": "420",
                "changeType": "same_setting",
                "title": "Bishop",
                "url": "https://sh1991.sacredharpbremen.org/420",
            },
            "sh2025": {
                "songNo": "420b",
                "changeType": "renumbered_in_2025",
                "title": "Bishop",
                "url": "https://sacredharpbremen.org/420b-bishop",
            },
        },
    },
    ("sh2025", "420b"): {
        "books": ["sh1991", "sh2025"],
        "status": "same-setting-renumbered",
        "relationId": "sh-edition:420b",
        "relationType": "edition-pair",
        "records": {
            "sh1991": {
                "songNo": "420",
                "changeType": "same_setting",
                "title": "Bishop",
                "url": "https://sh1991.sacredharpbremen.org/420",
            },
            "sh2025": {
                "songNo": "420b",
                "changeType": "renumbered_in_2025",
                "title": "Bishop",
                "url": "https://sacredharpbremen.org/420b-bishop",
            },
        },
    },
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def find_first(element: ET.Element, name: str) -> str:
    for node in element.iter():
        if local_name(node.tag) == name and (node.text or "").strip():
            return (node.text or "").strip()
    return ""


def first_matching_url(row: dict[str, str]) -> str | None:
    urls = re.findall(r"https?://[^;\s]+", (row.get("source_url", "") + ";" + row.get("notes", "")))
    for url in urls:
        if "shapenote.net/musicxml/" not in url:
            continue
        if row["book_id"] == "sh2025" and "cross-edition fallback" in row.get("notes", "").lower():
            return None
        cache_path = CACHE_ROOT / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.mxl"
        if cache_path.exists():
            return url
    return None


def first_reference_matching_url(row: dict[str, str]) -> str | None:
    """Return an explicitly marked alternate-edition MusicXML witness.

    2025 metadata sometimes carries a complete 1991 MusicXML fallback. It is
    useful for practice, but must stay a reference witness until compared with
    the 2025 engraving, so it never enters the exact-score path above.
    """
    if row.get("book_id") != "sh2025" or "cross-edition fallback" not in row.get("notes", "").lower():
        return None
    urls = re.findall(r"https?://[^;\s]+", row.get("source_url", "") + ";" + row.get("notes", ""))
    for url in urls:
        if "shapenote.net/musicxml/" not in url:
            continue
        cache_path = CACHE_ROOT / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.mxl"
        if cache_path.exists():
            return url
    return None


def source_urls(row: dict[str, str]) -> list[str]:
    urls = re.findall(r"https?://[^;\s]+", row.get("source_url", "") + ";" + row.get("notes", ""))
    return list(dict.fromkeys(urls))


def parse_score(url: str, source_path: Path | None = None) -> dict[str, Any] | None:
    cache_path = source_path or (CACHE_ROOT / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.mxl")
    try:
        with zipfile.ZipFile(cache_path) as archive:
            xml_names = [name for name in archive.namelist() if name.endswith(".xml") and "container" not in name]
            if not xml_names:
                return None
            root = ET.fromstring(archive.read(xml_names[0]))
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return None

    part_names: dict[str, str] = {}
    for score_part in root.iter():
        if local_name(score_part.tag) != "score-part":
            continue
        part_id = score_part.attrib.get("id")
        if part_id:
            part_names[part_id] = child_text(score_part, "part-name") or part_id

    global_key = ""
    global_time = ""
    musicxml_key_declarations: list[dict[str, Any]] = []
    shape_names = {"fa", "sol", "la", "mi", "do", "re", "ti"}
    parts: list[dict[str, Any]] = []
    used_part_names: dict[str, int] = {}
    for part in root:
        if local_name(part.tag) != "part":
            continue
        part_name = part_names.get(part.attrib.get("id", ""), part.attrib.get("id", "Part"))
        events: list[dict[str, Any]] = []
        current_clefs: dict[str, str] = {}
        default_clef = "treble"
        cursor = 0.0
        divisions = 1.0
        for measure in part:
            if local_name(measure.tag) != "measure":
                continue
            # MusicXML's <chord/> flag makes a note share the onset of the
            # immediately preceding note in the same voice/staff stream. It
            # does not mean "use the current cursor"; the cursor has already
            # advanced for the chord's anchor note. Keep this scoped to the
            # current measure and clear it when backup/forward changes the
            # document stream so a malformed chord cannot inherit a stale
            # onset from another voice.
            previous_note: tuple[tuple[str, str], float] | None = None
            measure_max_cursor = cursor
            for item in measure:
                item_name = local_name(item.tag)
                if item_name == "attributes":
                    divisions_text = child_text(item, "divisions")
                    if divisions_text:
                        try:
                            divisions = float(divisions_text)
                        except ValueError:
                            divisions = 1.0
                    key = next((n for n in item if local_name(n.tag) == "key"), None)
                    if key is not None:
                        fifths = child_text(key, "fifths")
                        mode = child_text(key, "mode")
                        if fifths:
                            musicxml_key_declarations.append(
                                {
                                    "fifths": fifths,
                                    "mode": mode,
                                    "modePresent": bool(mode),
                                }
                            )
                        if fifths and mode:
                            global_key = f"{fifths}:{mode}"
                        elif fifths:
                            # A missing MusicXML mode is not evidence of major.
                            # Keep the raw fifths in provenance, but fail closed
                            # until an edition/source key supplies the mode.
                            global_key = ""
                    time = next((n for n in item if local_name(n.tag) == "time"), None)
                    if time is not None:
                        time_beats = child_text(time, "beats")
                        beat_type = child_text(time, "beat-type")
                        if time_beats and beat_type:
                            global_time = f"{time_beats}/{beat_type}"
                    for clef in (n for n in item if local_name(n.tag) == "clef"):
                        sign = child_text(clef, "sign").upper()
                        line = child_text(clef, "line")
                        octave_change = child_text(clef, "clef-octave-change")
                        clef_name = {"G": "treble", "C": "alto", "F": "bass"}.get(sign, default_clef)
                        if octave_change == "-1":
                            clef_name = "tenor"
                        current_clefs[clef.attrib.get("number", "1")] = clef_name
                        if clef.attrib.get("number", "1") == "1":
                            default_clef = clef_name
                elif item_name == "backup":
                    try:
                        cursor -= float(find_first(item, "duration")) / divisions
                    except ValueError:
                        pass
                    previous_note = None
                    measure_max_cursor = max(measure_max_cursor, cursor)
                elif item_name == "forward":
                    try:
                        cursor += float(find_first(item, "duration")) / divisions
                    except ValueError:
                        pass
                    previous_note = None
                    measure_max_cursor = max(measure_max_cursor, cursor)
                elif item_name == "note":
                    duration_text = child_text(item, "duration")
                    try:
                        beats = float(duration_text) / divisions if duration_text else 0.5
                    except ValueError:
                        beats = 0.5
                    chord = any(local_name(child.tag) == "chord" for child in item)
                    voice = child_text(item, "voice")
                    staff = child_text(item, "staff") or "1"
                    stream = (voice, staff)
                    note_onset = cursor
                    if chord and previous_note is not None and previous_note[0] == stream:
                        note_onset = previous_note[1]
                    pitch = next((node for node in item if local_name(node.tag) == "pitch"), None)
                    event: dict[str, Any] = {
                        "onset": round(note_onset, 3),
                        "beats": round(max(beats, 0.125), 3),
                        "measure": measure.attrib.get("number", ""),
                        "rest": pitch is None,
                        "voice": voice,
                        "staff": staff,
                        "type": child_text(item, "type"),
                        "dots": sum(1 for child in item if local_name(child.tag) == "dot"),
                        "accidental": child_text(item, "accidental"),
                        "notehead": child_text(item, "notehead"),
                        "clef": current_clefs.get(child_text(item, "staff") or "1", default_clef),
                    }
                    if pitch is not None:
                        event.update(
                            {
                                "step": child_text(pitch, "step"),
                                "alter": int(child_text(pitch, "alter") or "0"),
                                "octave": int(child_text(pitch, "octave") or "4"),
                            }
                        )
                    if event.get("notehead", "").lower() in shape_names:
                        event["shape"] = event["notehead"].lower()
                    for tie in (child for child in item if local_name(child.tag) == "tie"):
                        tie_type = tie.attrib.get("type", "")
                        if tie_type in {"start", "stop"}:
                            event[f"tie{tie_type.title()}"] = True
                    event = {key: value for key, value in event.items() if value not in ("", 0, False, None) or key in {"onset", "beats", "measure", "rest", "staff", "dots"}}
                    events.append(event)
                    previous_note = (stream, note_onset)
                    measure_max_cursor = max(measure_max_cursor, note_onset + beats)
                    if not chord:
                        cursor += beats
            # A MusicXML measure can contain multiple voices separated by
            # backup/forward. The final cursor may belong to a shorter voice;
            # the next measure starts after the furthest event in this one.
            cursor = measure_max_cursor
        if events:
            display_name = part_name.title()
            used_part_names[display_name] = used_part_names.get(display_name, 0) + 1
            if used_part_names[display_name] > 1:
                display_name = f"{display_name} {used_part_names[display_name]}"
            parts.append({"name": display_name, "clefs": current_clefs, "events": events})

    score = {
        "sourceUrl": url,
        "workTitle": find_first(root, "work-title"),
        "keySignature": global_key,
        "timeSignature": global_time,
        "musicXmlKeyDeclarations": musicxml_key_declarations,
        "parts": parts,
    } if parts else None
    if score:
        score["keyEvidence"] = {
            "status": "source-verified" if global_key else "unknown",
            "source": "structured MusicXML source" if global_key else "not encoded in structured source",
        }
        return prepare_score_for_playback(score)
    return None


KEY_SIGNATURE_FIFTHS = {
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "C#": 7,
    "F": -1,
    "Bb": -2,
    "Eb": -3,
    "Ab": -4,
    "Db": -5,
    "Gb": -6,
    "Cb": -7,
}
MINOR_KEY_SIGNATURE_FIFTHS = {
    "A": 0,
    "E": 1,
    "B": 2,
    "F#": 3,
    "C#": 4,
    "G#": 5,
    "D#": 6,
    "A#": 7,
    "D": -1,
    "G": -2,
    "C": -3,
    "F": -4,
    "Bb": -5,
    "Eb": -6,
    "Ab": -7,
}


def source_key_to_musicxml(key: str) -> str:
    """Convert a source label such as ``E minor`` to ``fifths:mode``."""
    normalized = str(key or "").strip().replace("♯", "#").replace("♭", "b")
    normalized = re.sub(r"(?i)-sharp\b", "#", normalized)
    normalized = re.sub(r"(?i)-flat\b", "b", normalized)
    match = re.fullmatch(r"([A-Ga-g](?:#|b)?)\s+(major|minor)", normalized, re.IGNORECASE)
    if not match:
        return ""
    tonic = match.group(1)[0].upper() + match.group(1)[1:]
    mode = match.group(2).lower()
    fifths = (MINOR_KEY_SIGNATURE_FIFTHS if mode == "minor" else KEY_SIGNATURE_FIFTHS).get(tonic)
    return f"{fifths}:{mode}" if fifths is not None else ""


def annotate_raw_key_conflict(score: dict[str, Any], resolved_key: str) -> None:
    """Record a source-key versus raw-OMR fifths conflict without rewriting it."""
    expected = source_key_to_musicxml(resolved_key)
    if not expected:
        return
    expected_fifths = expected.split(":", 1)[0]
    declarations = score.get("musicXmlKeyDeclarations") or []
    raw_fifths = sorted({str(item.get("fifths", "")) for item in declarations if item.get("fifths", "")})
    conflicting_fifths = sorted(set(raw_fifths) - {expected_fifths})
    if not conflicting_fifths:
        return
    score.setdefault("keyEvidence", {})["rawFifthsConflict"] = {
        "resolvedSourceKey": expected,
        "rawFifths": raw_fifths,
        "conflictingFifths": conflicting_fifths,
        "modePresent": any(item.get("modePresent") is True for item in declarations),
        "status": "preserved-conflict",
    }
    score["omrDetectedKeySignature"] = f"fifths={','.join(raw_fifths)};mode-missing"


def apply_source_key_to_score(score: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Overlay a verified edition key on a derived asset without changing raw input."""
    source_key = str(metadata.get("keySignature", ""))
    source_key_value = source_key_to_musicxml(source_key)
    if not source_key_value or metadata.get("keyEvidence", {}).get("status") != "source-verified":
        return score
    corrected = copy.deepcopy(score)
    declared_key = corrected.get("keySignature", "")
    if declared_key and declared_key != source_key_value:
        corrected["musicXmlDeclaredKeySignature"] = declared_key
    corrected["keySignature"] = source_key_value
    corrected["keyEvidence"] = {
        "status": "source-verified",
        "source": "edition-specific source metadata",
    }
    annotate_raw_key_conflict(corrected, source_key_value)
    return corrected


def prepare_score_for_playback(score: dict[str, Any]) -> dict[str, Any]:
    """Preserve every parsed source event for playback and transposition.

    A previous implementation removed synchronized final chords as a
    defensive workaround for malformed chord timing. That silently dropped
    legitimate source material and hid parser errors. MusicXML is now parsed
    with correct ``<chord/>`` onsets, so the source event stream remains
    intact. The transform metadata is retained for schema compatibility and
    makes the no-data-loss policy explicit.
    """
    if score.get("playbackTransform"):
        return score
    score["playbackTransform"] = {
        "finalChordRemoved": False,
        "reason": "source-final-chord-preserved",
        "removedEventCount": 0,
        "sourcePreserved": True,
    }
    return score


def score_asset(url: str, score: dict[str, Any], asset_key: str | None = None) -> dict[str, Any]:
    """Write the complete score once and return a compact index record."""
    score = prepare_score_for_playback(score)
    score.setdefault("keyEvidence", {
        "status": "source-verified" if score.get("keySignature") else "unknown",
        "source": "structured MusicXML source" if score.get("keySignature") else "not encoded in structured source",
    })
    _add_transposition_capability(score)
    identity = asset_key or url
    asset_name = f"{hashlib.sha256(identity.encode()).hexdigest()[:24]}.json"
    asset_path = SCORES_OUTPUT / asset_name
    asset_path.write_text(json.dumps(score, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    preview = dict(score)
    preview["scoreRef"] = f"/scores/{asset_name}"
    preview["parts"] = [{"name": part["name"], "events": []} for part in score["parts"]]
    return preview


def draft_score_asset(draft_key: str, score: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Write an isolated, clearly-labeled OMR draft asset for review playback."""
    score = prepare_score_for_playback(score)
    source_measure_counts = {
        str(part.get("id") or index + 1): int(part.get("measures", 0))
        for index, part in enumerate(draft.get("parts", []))
        if part.get("measures") is not None
    }
    if source_measure_counts:
        score["sourceMeasureCounts"] = source_measure_counts
        score["sourceMeasureCount"] = max(source_measure_counts.values())
    _add_transposition_capability(score)
    digest = hashlib.sha256(f"{draft_key}:{draft.get('sha256', '')}".encode()).hexdigest()[:24]
    asset_name = f"{digest}.json"
    asset_path = DRAFT_SCORES_OUTPUT / asset_name
    asset_path.write_text(json.dumps(score, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    preview = dict(score)
    preview["scoreRef"] = f"/draft-scores/{asset_name}"
    preview["provenance"] = {
        "kind": "omr-draft",
        "label": "Unverified transcription draft",
        "reviewRequired": True,
        "sourceEdition": "sh2025",
        "sourceRecordKey": draft_key.split("/", 1)[-1],
        "sourceArtifact": str(draft.get("artifact", "")),
        "sourceSha256": str(draft.get("sha256", "")),
    }
    key_evidence = score.get("keyEvidence", {})
    preview["provenance"]["sourceKeyVerified"] = key_evidence.get("status") == "source-verified"
    preview["provenance"]["keySource"] = key_evidence.get("source", "not recorded")
    if score.get("omrDetectedKeySignature"):
        preview["provenance"]["omrDetectedKeySignature"] = score["omrDetectedKeySignature"]
    preview["parts"] = [{"name": part["name"], "events": []} for part in score["parts"]]
    return preview


def _add_transposition_capability(score: dict[str, Any]) -> None:
    """Record the fail-closed transposition capability beside each score."""
    has_pitched_events = any(
        not event.get("rest") and event.get("step") and event.get("octave") is not None
        for part in score.get("parts", [])
        for event in part.get("events", [])
    )
    key_status = score.get("keyEvidence", {}).get("status", "unknown")
    key_is_usable = key_status in {"source-verified", "source-observed", "omr-detected"} and bool(score.get("keySignature"))
    score["transposition"] = {
        "available": bool(has_pitched_events and key_is_usable),
        "hasPitchedEvents": bool(has_pitched_events),
        "manualKeyAllowed": bool(has_pitched_events and not key_is_usable),
        "keyStatus": key_status,
        "reason": "available"
        if has_pitched_events and key_is_usable
        else "manual-source-key-required"
        if has_pitched_events
        else "no-usable-pitched-events",
    }


def score_provenance(
    book_id: str, url: str, manifest_entry: dict[str, Any] | None = None
) -> dict[str, str]:
    """Classify a parsed score without conflating a witness with an edition.

    The public catalog's 2025 section includes useful files from other
    tunebooks. They remain valuable reference scores, but only files named as
    SH25 sources are admitted as the 2025 edition's transposable score until
    an edition-specific witness is available.
    """
    stem = Path(unquote(urlparse(url).path)).stem.lower()
    if manifest_entry and manifest_entry.get("sourceEdition") == book_id:
        return {
            "kind": "edition-source",
            "label": "Transposable source score",
        }
    if book_id == "sh2025" and not stem.startswith("sh25-") and url not in EXACT_SCORE_URLS:
        return {
            "kind": "alternate-source",
            "label": "Transposable reference · other edition/source",
        }
    return {
        "kind": "edition-source",
        "label": "Transposable source score",
    }


def existing_score_asset(url: str) -> dict[str, Any] | None:
    cache_path = CACHE_ROOT / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.mxl"
    if cache_path.exists():
        parsed = parse_score(url, cache_path)
        if parsed:
            return parsed
    asset_path = SCORES_OUTPUT / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.json"
    if not asset_path.exists():
        return None
    try:
        score = json.loads(asset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return score if score.get("sourceUrl") == url and score.get("parts") else None


def load_dashboard_data() -> dict[str, Any]:
    text = SOURCE_DATA.read_text(encoding="utf-8")
    prefix = "window.SH_CORPUS_DATA = "
    if prefix not in text:
        raise RuntimeError(f"Expected {prefix!r} in {SOURCE_DATA}")
    payload = text.split(prefix, 1)[1].rsplit(";", 1)[0].strip()
    return json.loads(payload)


def change_payload(row: dict[str, str]) -> dict[str, str]:
    return {
        "changeType": row.get("change_type", ""),
        "textKey": row.get("text_key", ""),
        "title": row.get("title", ""),
        "url": row.get("url", ""),
    }


def source_metadata_differences(metadata_by_book: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Return source-field disagreements that must be visible in an edition pair."""
    differences: dict[str, dict[str, str]] = {}
    for field in ("keySignature", "mode", "timeSignature"):
        left = metadata_by_book.get("sh1991", {}).get(field, "")
        right = metadata_by_book.get("sh2025", {}).get(field, "")
        if left and right and left != right:
            differences[field] = {
                "sh1991": left,
                "sh2025": right,
            }
    return differences


def load_edition_changes() -> dict[str, dict[str, list[dict[str, str]]]]:
    changes: dict[str, dict[str, list[dict[str, str]]]] = {}
    if not EDITION_CHANGES.exists():
        return changes
    with EDITION_CHANGES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            song_changes = changes.setdefault(row["song_no"].lower(), {})
            song_changes.setdefault(row["book_id"], []).append(change_payload(row))
    return changes


def load_edition_relations() -> dict[tuple[str, str], dict[str, Any]]:
    """Pair one 1991 and one 2025 change-register row without merging records."""
    grouped: dict[str, list[dict[str, str]]] = {}
    if not EDITION_CHANGES.exists():
        return {}
    with EDITION_CHANGES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped.setdefault(row["song_no"].lower(), []).append(row)
    relations: dict[tuple[str, str], dict[str, Any]] = {}
    for song_no, rows in grouped.items():
        if len(rows) != 2 or {row["book_id"] for row in rows} != {"sh1991", "sh2025"}:
            continue
        records = {row["book_id"]: {"songNo": row["song_no"], **change_payload(row)} for row in rows}
        relation = {
            "relationId": f"sh-edition:{song_no}",
            "relationType": "edition-pair",
            "records": records,
        }
        for row in rows:
            relations[(row["book_id"], row["song_no"].lower())] = relation
    return relations


def load_transcription_audits() -> dict[str, dict[str, Any]]:
    audits: dict[str, dict[str, Any]] = {}
    if not TRANSCRIPTION_ROOT.exists():
        return audits
    for path in TRANSCRIPTION_ROOT.rglob("*.audit.json"):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record = str(audit.get("record", "")).lower()
        if record:
            audits[record] = audit
    return audits


def load_omr_drafts() -> dict[str, dict[str, Any]]:
    """Load local OMR work product without treating it as verified notation."""
    if not DRAFT_INDEX.exists():
        return {}
    try:
        payload = json.loads(DRAFT_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    drafts: dict[str, dict[str, Any]] = {}
    for draft in payload.get("records", []):
        record = str(draft.get("record", "")).lower()
        match = re.match(r"(\d+[a-z]?)", record)
        if not match:
            continue
        draft_path = PROJECT_ROOT / str(draft.get("artifact", ""))
        if not draft_path.exists():
            continue
        drafts[f"sh2025/{match.group(1)}"] = {**draft, "artifactPath": draft_path}
    return drafts


def load_source_recordings() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in (SOURCE_RECORDINGS, SOURCE_DEBUT_RECORDINGS):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key, entry in payload.get("records", {}).items():
            target = merged.setdefault(key, {"tracks": [], "sourcePages": []})
            for track in entry.get("tracks", []):
                if track.get("url") and track["url"] not in {item.get("url") for item in target["tracks"]}:
                    target["tracks"].append(track)
            for page_key in ("sourcePage", "sourceCollectionUrl"):
                value = entry.get(page_key, "")
                if value and value not in target["sourcePages"]:
                    target["sourcePages"].append(value)
            if entry.get("sourcePage") and not target.get("sourcePage"):
                target["sourcePage"] = entry["sourcePage"]
            if entry.get("sourceCollectionUrl") and not target.get("sourceCollectionUrl"):
                target["sourceCollectionUrl"] = entry["sourceCollectionUrl"]
    return merged


def load_source_images() -> dict[str, dict[str, str]]:
    if not SOURCE_IMAGE_MANIFEST.exists():
        return {}
    try:
        payload = json.loads(SOURCE_IMAGE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload.get("records", {})


def load_source_metadata_observations() -> dict[str, dict[str, Any]]:
    """Load compact source-page observations without promoting OCR metadata."""
    if not SOURCE_METADATA_OBSERVATIONS.exists():
        return {}
    try:
        payload = json.loads(SOURCE_METADATA_OBSERVATIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(record.get("queueId", "")).lower(): record
        for record in payload.get("records", [])
        if record.get("queueId")
    }


def load_shapenote_2025_score_audit() -> dict[str, dict[str, Any]]:
    """Load the fail-closed audit for the 25 cataloged 2025 MXL entries."""
    if not SHAPENOTE_2025_SCORE_AUDIT.exists():
        return {}
    try:
        payload = json.loads(SHAPENOTE_2025_SCORE_AUDIT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(record.get("queueId", "")).lower(): record
        for record in payload.get("records", [])
        if record.get("queueId")
    }


def attach_source_metadata_observation(
    coverage_record: dict[str, Any], observation: dict[str, Any] | None
) -> None:
    """Attach review-only source observations while keeping them non-authoritative."""
    if not observation:
        return
    source = observation.get("source", {})
    observed = observation.get("observations", {})
    coverage_record["sourceMetadataObservation"] = {
        "status": "review-only-source-observation",
        "source": {
            "imagePath": source.get("imagePath", ""),
            "imageSha256": source.get("imageSha256", ""),
            "immutable": source.get("immutable") is True,
        },
        "key": observed.get("key", {}),
        "meter": observed.get("meter", {}),
        "parts": observed.get("parts", {}),
        "humanReviewRequired": observation.get("humanReviewRequired") is True,
        "safeToPromote": False,
        "ocr": {
            "engine": observation.get("ocr", {}).get("engine", ""),
            "rawTextPath": observation.get("ocr", {}).get("rawTextPath", ""),
            "rawTextSha256": observation.get("ocr", {}).get("rawTextSha256", ""),
        },
    }


def source_observed_key(observation: dict[str, Any] | None) -> str:
    if not observation:
        return ""
    key = observation.get("observations", {}).get("key", {})
    if key.get("status") != "observed-from-source-image-ocr":
        return ""
    return str(key.get("value", ""))


def authoritative_metadata_key(
    row: dict[str, str], audit: dict[str, Any] | None,
    direct_source: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, str] | None]:
    """Return only a source-authoritative key from edition metadata.

    The metadata export carries 2025 cross-edition fallback keys so
    acquisition work can be prioritized. Those values are useful candidates,
    but they are not evidence for the 2025 engraving because the revision
    changed keys. An explicit transcription audit is stronger and wins over
    a secondary candidate.
    """
    direct_key = str((direct_source or {}).get("key", "")).strip()
    if direct_key:
        return direct_key, {
            "status": "source-verified",
            "source": direct_source.get("source", "direct source evidence"),
            "sourceImageUrl": direct_source.get("sourceImageUrl", ""),
            "sourceImageSha256": direct_source.get("sourceImageSha256", ""),
            "observation": direct_source.get("observation", ""),
        }, None

    audited_key = str((audit or {}).get("sourceKey", "")).strip()
    if audited_key:
        return audited_key, {
            "status": "source-verified",
            "source": "source audit",
        }, None

    metadata_key = str(row.get("key_signature", "")).strip()
    if not metadata_key:
        return "", {"status": "unknown", "source": "not recorded"}, None

    confidence = str(row.get("confidence", "")).strip().lower()
    if confidence == "source":
        return metadata_key, {
            "status": "source-verified",
            "source": "source metadata",
        }, None

    # Keep the fallback available for audit tooling without allowing it to
    # drive transposition or appear as an authoritative edition key.
    return "", {
        "status": "unknown",
        "source": "secondary metadata only; edition source not verified",
    }, {
        "value": metadata_key,
        "status": "secondary",
        "source": "cross-edition fallback metadata",
    }


def load_clean_source_candidates() -> dict[str, list[dict[str, Any]]]:
    """Load public clean-source leads for the acquisition queue only."""
    if not SOURCE_CLEAN_CANDIDATES.exists():
        return {}
    try:
        payload = json.loads(SOURCE_CLEAN_CANDIDATES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    candidates: dict[str, list[dict[str, Any]]] = {}
    omr_by_key: dict[str, dict[str, Any]] = {}
    if SOURCE_CLEAN_OMR_RUN.exists():
        try:
            omr_payload = json.loads(SOURCE_CLEAN_OMR_RUN.read_text(encoding="utf-8"))
            omr_by_key = {
                str(item.get("candidateKey")): item
                for item in omr_payload.get("records", [])
                if item.get("candidateKey")
            }
        except (OSError, json.JSONDecodeError):
            omr_by_key = {}
    for item in payload.get("records", []):
        if item.get("status") != "candidate-source-needs-edition-comparison":
            continue
        song_no = str(item.get("songNo", "")).lower()
        if not song_no or not item.get("pdfUrl"):
            continue
        omr = omr_by_key.get(str(item.get("candidateKey", "")), {})
        candidates.setdefault(f"sh2025/{song_no}", []).append(
            {
                "title": item.get("candidateTitle", ""),
                "candidateKey": item.get("candidateKey", ""),
                "pageUrl": item.get("candidatePageUrl", ""),
                "pdfUrl": item.get("pdfUrl", ""),
                "localPdf": item.get("localPdf", ""),
                "sha256": item.get("sha256", ""),
                "omrInputPdf": item.get("omrInputPdf", ""),
                "omrInputSha256": item.get("omrInputSha256", ""),
                "compositePdfPage": item.get("compositePdfPage"),
                "matchKind": item.get("matchKind", ""),
                "status": item.get("status", ""),
                "editionVerified": False,
                "structuredScoreAdmissible": False,
                "omrStatus": omr.get("status", "not-run"),
                "omrArtifacts": omr.get("draftArtifacts", []),
                "omrLog": omr.get("log", ""),
                "omrCandidateKey": omr.get("candidateKey", ""),
            }
        )
    return candidates


def attach_clean_source_candidates(
    coverage_record: dict[str, Any],
    candidates: dict[str, list[dict[str, Any]]],
    book_id: str,
    song_key: str,
    metadata_key: str = "",
) -> None:
    """Expose comparison leads on the record without treating them as scores."""
    keys = [f"{book_id}/{song_key}".lower()]
    if metadata_key and metadata_key.lower() != song_key.lower():
        keys.append(f"{book_id}/{metadata_key}".lower())
    for key in keys:
        if candidates.get(key):
            coverage_record["cleanSourceCandidates"] = candidates[key]
            return


def load_edition_additions() -> dict[str, Any]:
    """Load the publisher's edition-level additions register.

    This is evidence about editorial status, not notation. It lets the atlas
    distinguish genuinely new 2025 material from retained or revised pages
    without using that distinction as permission to synthesize a score.
    """
    if not EDITION_ADDITIONS_2025.exists():
        return {}
    try:
        payload = json.loads(EDITION_ADDITIONS_2025.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records = [str(record).lower() for record in payload.get("records", [])]
    return {
        "edition": payload.get("edition", "sh2025"),
        "sourceUrl": payload.get("sourceUrl", ""),
        "sourceLabel": payload.get("sourceLabel", ""),
        "count": int(payload.get("count", len(records))),
        "records": records,
    }


def edition_evidence(book_id: str, song_no: str, additions: dict[str, Any]) -> dict[str, Any]:
    """Return source-backed 2025 addition status for one edition record."""
    if book_id != "sh2025" or not additions.get("sourceUrl"):
        return {}
    added = song_no.lower() in set(additions.get("records", []))
    return {
        "editionStatus": "added-in-2025" if added else "not-new-in-2025",
        "editionEvidenceUrl": additions["sourceUrl"],
        "editionEvidenceLabel": additions.get("sourceLabel", ""),
    }


def apply_current_2025_index(data: dict[str, Any], metadata: dict[tuple[str, str], dict[str, str]]) -> None:
    """Align the display corpus with the current authoritative 2025 index.

    The local export still contains a superseded 414b record and a hallucinated
    264b record, while omitting three records now listed by Fasola. Preserve
    the genuinely useful superseded 414b record in an audit field, discard the
    hallucinated 264b record, and do not expose either as current 2025 pages.
    """
    songs = data["songs"]
    legacy_records: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    for song in songs:
        if song.get("books") == ["sh2025"] and song.get("songNo", "").lower() == "264b":
            continue
        if song.get("books") == ["sh2025"] and song.get("songNo", "").lower() == "414b":
            legacy_records.append({
                "bookId": "sh2025",
                "songNo": song.get("songNo", ""),
                "title": song.get("title", ""),
                "reason": "not-listed-in-current-fasola-2025-index",
                "record": song,
            })
            continue
        retained.append(song)
    songs[:] = retained

    shared_106 = next((song for song in songs if song.get("songNo", "").lower() == "106" and "sh1991" in song.get("books", [])), None)
    if shared_106 and "sh2025" not in shared_106["books"]:
        shared_106["books"].append("sh2025")
        shared_106.setdefault("titlesByBook", {})["sh2025"] = "Ecstasy"
        shared_106.setdefault("textKeysByBook", {})["sh2025"] = shared_106.get("textKey", "")
        shared_106.setdefault("urls", []).append("https://fasola.org/indexes/2025/?p=106")

    for song_no, values in CURRENT_2025_INDEX_ADDITIONS.items():
        row = metadata.get(("sh2025", song_no))
        if not row:
            continue
        songs.append({
            "id": f"sh {song_no} (sh2025) — {values['title']}",
            "songNo": song_no,
            "songNoSort": [int(re.match(r"\d+", song_no).group()), 1, "t"],
            "title": values["title"],
            "textKey": values["textKey"],
            "bookFamily": "sh",
            "displayFamily": "sh",
            "mergeFamily": "sh",
            "books": ["sh2025"],
            "sourceFamilies": ["sh"],
            "titlesByBook": {"sh2025": values["title"]},
            "textKeysByBook": {"sh2025": values["textKey"]},
            "urls": [values["sourceUrl"]],
            "rawFirstLine": values["rawFirstLine"],
            "textHub": f"text--{values['textKey'].replace(' ', '-')}" ,
            "path": f"fasola.org/indexes/2025/?p={song_no}",
        })

    data["songs"] = sorted(songs, key=lambda song: tuple(song.get("songNoSort", [10**9, 99, song.get("id", "")])) + (song.get("id", ""),))
    if legacy_records:
        data["legacyEditionRecords"] = legacy_records


def source_coverage_record(
    book_id: str,
    row: dict[str, str] | None,
    source_urls_for_record: list[str],
    score: dict[str, Any] | None,
    manifest_entry: dict[str, str] | None,
    audit: dict[str, Any] | None,
    recording: dict[str, Any] | None = None,
    source_record_key: str = "",
) -> dict[str, Any]:
    """Describe the safe next step for one edition-specific song record.

    A URL is deliberately called a ``source-reference`` rather than an
    available scan: a link can be dead, paywalled, or metadata-only. Only a
    parsed local score earns ``structured-score`` status.
    """
    audit_status = str((audit or {}).get("status", ""))
    transcription_status = str((audit or {}).get("transcriptionStatus", ""))
    blocked = audit_status == "blocked" or transcription_status in {"blocked", "acquisition_needed"}
    if score:
        record = {
            "status": "structured-score",
            "nextAction": "verify-source-fidelity-and-playback",
            "sourceUrls": source_urls_for_record,
            "sourceUrlCount": len(source_urls_for_record),
            "sourceRecordKey": row.get("song_no", "") if row else source_record_key,
            "manifestSourceUrl": (manifest_entry or {}).get("sourceUrl", ""),
            "manifestRawPath": (manifest_entry or {}).get("rawPath", ""),
        }
    elif row is None:
        record = {
            "status": "source-reference" if source_urls_for_record else "mapping-gap",
            "nextAction": "transcribe-and-verify" if source_urls_for_record else "repair-corpus-mapping",
            "sourceUrls": [],
            "sourceUrlCount": 0,
            "sourceRecordKey": source_record_key,
            "manifestSourceUrl": "",
            "manifestRawPath": "",
        }
        record["sourceUrls"] = source_urls_for_record
        record["sourceUrlCount"] = len(source_urls_for_record)
    elif blocked:
        record = {
            "status": "transcription-blocked",
            "nextAction": "acquire-authorized-source",
            "sourceUrls": source_urls_for_record,
            "sourceUrlCount": len(source_urls_for_record),
            "sourceRecordKey": row.get("song_no", ""),
            "manifestSourceUrl": (manifest_entry or {}).get("sourceUrl", ""),
            "manifestRawPath": (manifest_entry or {}).get("rawPath", ""),
        }
    elif source_urls_for_record:
        record = {
            "status": "source-reference",
            "nextAction": "transcribe-and-verify",
            "sourceUrls": source_urls_for_record,
            "sourceUrlCount": len(source_urls_for_record),
            "sourceRecordKey": row.get("song_no", ""),
            "manifestSourceUrl": (manifest_entry or {}).get("sourceUrl", ""),
            "manifestRawPath": (manifest_entry or {}).get("rawPath", ""),
        }
    else:
        record = {
            "status": "metadata-only",
            "nextAction": "acquire-authorized-source",
            "sourceUrls": source_urls_for_record,
            "sourceUrlCount": len(source_urls_for_record),
            "sourceRecordKey": row.get("song_no", ""),
            "manifestSourceUrl": (manifest_entry or {}).get("sourceUrl", ""),
            "manifestRawPath": (manifest_entry or {}).get("rawPath", ""),
        }
    if audit:
        record["auditStatus"] = audit_status
        record["transcriptionStatus"] = transcription_status
        record["blockedReason"] = audit.get("blockedReason", "")
        record["acquisitionNeeded"] = audit.get("acquisitionNeeded", "")
        record["localArtifacts"] = audit.get("localArtifacts", {})
    if recording and recording.get("tracks"):
        record["recordingTracks"] = recording["tracks"]
        record["recordingSourcePage"] = recording.get("sourcePage", "")
        record["recordingSourcePages"] = recording.get("sourcePages", [])
        record["recordingSourceCollectionUrl"] = recording.get("sourceCollectionUrl", "")
    if manifest_entry:
        source_sha256 = str(manifest_entry.get("sourceSha256", ""))
        source_bytes = manifest_entry.get("sourceBytes")
        source_edition = str(manifest_entry.get("sourceEdition", ""))
        if source_sha256:
            record["manifestSourceSha256"] = source_sha256
        if isinstance(source_bytes, int):
            record["manifestSourceBytes"] = source_bytes
        if source_edition:
            record["manifestSourceEdition"] = source_edition
        catalog_section = str(manifest_entry.get("catalogSection", ""))
        catalog_label = str(manifest_entry.get("label", ""))
        if catalog_section:
            record["manifestCatalogSection"] = catalog_section
        if catalog_label:
            record["manifestCatalogLabel"] = catalog_label
    return record


def transcription_priority(status: str) -> int:
    """Order work by the dependency that must be repaired first."""
    return {
        "mapping-gap": 0,
        "transcription-blocked": 1,
        "metadata-only": 1,
        "source-reference": 2,
    }.get(status, 9)


def main() -> int:
    if not SOURCE_DATA.exists() or not SOURCE_METADATA.exists():
        print("Local corpus source files are missing; refusing to build a partial bundle.", file=sys.stderr)
        return 1

    data = load_dashboard_data()
    edition_changes = load_edition_changes()
    edition_relations = load_edition_relations()
    transcription_audits = load_transcription_audits()
    transcription_drafts = load_omr_drafts()
    source_recordings = load_source_recordings()
    source_images = load_source_images()
    source_metadata_observations = load_source_metadata_observations()
    shapenote_2025_score_audit = load_shapenote_2025_score_audit()
    clean_source_candidates = load_clean_source_candidates()
    edition_additions = load_edition_additions()
    metadata: dict[tuple[str, str], dict[str, str]] = {}
    with SOURCE_METADATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            metadata[(row["book_id"], row["song_no"].lower())] = row
    apply_current_2025_index(data, metadata)

    remote_entries: dict[str, dict[str, str]] = {}
    if REMOTE_MANIFEST.exists():
        remote_payload = json.loads(REMOTE_MANIFEST.read_text(encoding="utf-8"))
        remote_entries = remote_payload.get("entries", {})
    remote_entries_by_url = {
        entry.get("sourceUrl"): entry
        for entry in remote_entries.values()
        if entry.get("sourceUrl")
    }

    score_cache: dict[str, dict[str, Any] | None] = {}
    draft_cache: dict[str, dict[str, Any] | None] = {}
    SCORES_OUTPUT.mkdir(parents=True, exist_ok=True)
    DRAFT_SCORES_OUTPUT.mkdir(parents=True, exist_ok=True)
    songs: list[dict[str, Any]] = []
    local_scores = 0
    score_parts = 0
    book_coverage = {
        book_id: {
            "records": 0,
            "localScoreRecords": 0,
            "localScoreParts": 0,
            "sourceReferenceRecords": 0,
            "metadataOnlyRecords": 0,
            "mappingGapRecords": 0,
            "transposableRecords": 0,
            "transposableLocalScoreRecords": 0,
            "transposableReferenceRecords": 0,
            "transposableDraftRecords": 0,
            "keyUnknownStructuredRecords": 0,
        }
        for book_id in data["books"]
    }
    source_coverage_records: list[dict[str, Any]] = []
    score_records: dict[tuple[str, str], bool] = {}
    for song in data["songs"]:
        enriched = dict(song)
        metadata_by_book: dict[str, dict[str, str]] = {}
        score_by_book: dict[str, dict[str, Any]] = {}
        reference_score_by_book: dict[str, dict[str, Any]] = {}
        draft_score_by_book: dict[str, dict[str, Any]] = {}
        source_coverage_by_book: dict[str, dict[str, Any]] = {}
        for book_id in song["books"]:
            book_coverage.setdefault(book_id, {
                "records": 0,
                "localScoreRecords": 0,
                "localScoreParts": 0,
                "sourceReferenceRecords": 0,
                "metadataOnlyRecords": 0,
                "mappingGapRecords": 0,
                "transposableRecords": 0,
                "transposableLocalScoreRecords": 0,
                "transposableReferenceRecords": 0,
                "transposableDraftRecords": 0,
                "keyUnknownStructuredRecords": 0,
            })
            book_coverage[book_id]["records"] += 1
            song_key = song["songNo"].lower()
            source_metadata_observation = source_metadata_observations.get(f"{book_id}/{song_key}")
            row = metadata.get((book_id, song_key))
            metadata_key = song_key
            if row is None:
                metadata_key = METADATA_KEY_ALIASES.get(book_id, {}).get(song_key, song_key)
                row = metadata.get((book_id, metadata_key))
            image_entry = source_images.get(f"{book_id}/{song_key}")
            if image_entry is None and metadata_key != song_key:
                image_entry = source_images.get(f"{book_id}/{metadata_key}")
            source_image_url = (image_entry or {}).get("sourceImageUrl", "")
            if not row:
                catalog_source_urls = [
                    url for url in song.get("urls", [])
                    if isinstance(url, str) and url.startswith("https://")
                ]
                manifest_key = REMOTE_SCORE_ALIASES.get(book_id, {}).get(song_key, song_key)
                manifest_entry = remote_entries.get(f"{book_id}/{song_key}")
                if manifest_entry is None:
                    manifest_entry = remote_entries.get(f"{book_id}/{manifest_key}")
                if manifest_entry:
                    url = manifest_entry["sourceUrl"]
                    source_path = PROJECT_ROOT / manifest_entry["rawPath"]
                    cache_key = f"remote:{url}"
                    if cache_key not in score_cache:
                        score_cache[cache_key] = parse_score(url, source_path) if source_path.exists() else None
                    parsed_score = score_cache.get(cache_key)
                    if parsed_score:
                        score_preview = score_asset(url, parsed_score, asset_key=f"{book_id}:{url}")
                        score_preview["provenance"] = score_provenance(book_id, url, manifest_entry)
                        if score_preview["provenance"]["kind"] == "edition-source":
                            score_by_book[book_id] = score_preview
                            book_coverage[book_id]["localScoreRecords"] += 1
                            book_coverage[book_id]["localScoreParts"] += len(parsed_score["parts"])
                        else:
                            reference_score_by_book[book_id] = score_preview
                        score_records[(book_id, song_key)] = book_id in score_by_book
                        source_urls_with_score = list(dict.fromkeys(catalog_source_urls + [url]))
                        coverage_record = source_coverage_record(
                            book_id,
                            None,
                            source_urls_with_score,
                            parsed_score if score_preview["provenance"]["kind"] == "edition-source" else None,
                            manifest_entry,
                            None,
                            source_record_key=song_key,
                        )
                        coverage_record.update(edition_evidence(book_id, song_key, edition_additions))
                        if source_image_url:
                            coverage_record["sourceImageUrl"] = source_image_url
                        attach_source_metadata_observation(coverage_record, source_metadata_observation)
                        attach_clean_source_candidates(coverage_record, clean_source_candidates, book_id, song_key)
                        source_coverage_by_book[book_id] = coverage_record
                        continue
                coverage_record = source_coverage_record(
                    book_id,
                    None,
                    list(dict.fromkeys(catalog_source_urls)),
                    None,
                    None,
                    None,
                    source_record_key=song_key,
                )
                coverage_record.update(edition_evidence(book_id, song_key, edition_additions))
                if source_image_url:
                    coverage_record["sourceImageUrl"] = source_image_url
                attach_source_metadata_observation(coverage_record, source_metadata_observation)
                attach_clean_source_candidates(coverage_record, clean_source_candidates, book_id, song_key, metadata_key)
                source_coverage_by_book[book_id] = coverage_record
                if coverage_record["status"] == "source-reference":
                    book_coverage[book_id]["sourceReferenceRecords"] += 1
                else:
                    book_coverage[book_id]["mappingGapRecords"] += 1
                continue
            audit = transcription_audits.get(f"{book_id}/{song['songNo']}".lower())
            draft = transcription_drafts.get(f"{book_id}/{song['songNo']}".lower())
            recording = source_recordings.get(f"{book_id}/{song['songNo']}".lower())
            audit_urls = [
                value for value in (audit or {}).get("sourceWitnesses", {}).values()
                if isinstance(value, str) and value.startswith("http")
            ]
            all_source_urls = list(dict.fromkeys(source_urls(row) + audit_urls))
            source_override = EDITION_SOURCE_OVERRIDES.get((book_id, song_key)) or EDITION_SOURCE_OVERRIDES.get((book_id, metadata_key))
            if book_id == "sh2025" and not source_override:
                canonical_2025_url = f"https://fasola.org/indexes/2025/?p={song['songNo']}"
                source_override = {
                    "sourceUrl": canonical_2025_url,
                    "sourceUrls": [canonical_2025_url],
                }
            legacy_source_urls = list(all_source_urls)
            if source_override:
                all_source_urls = list(dict.fromkeys(source_override["sourceUrls"] + all_source_urls))
            direct_source_key = DIRECT_SOURCE_KEY_OVERRIDES.get((book_id, song_key)) or DIRECT_SOURCE_KEY_OVERRIDES.get((book_id, metadata_key))
            authoritative_key, key_evidence, key_candidate = authoritative_metadata_key(row, audit, direct_source_key)
            metadata_by_book[book_id] = {
                "meter": row.get("meter", ""),
                "timeSignature": row.get("time_signature", "") or str((audit or {}).get("sourceTimeSignature", "")),
                "keySignature": authoritative_key,
                "composer": row.get("composer", ""),
                "lyricist": row.get("lyricist", ""),
                "sourceUrl": source_override["sourceUrl"] if source_override else row.get("source_url", "").split(";", 1)[0],
                "sourceUrls": all_source_urls,
                "sourceRecordKey": metadata_key,
                "confidence": row.get("confidence", ""),
                "notes": row.get("notes", ""),
            }
            if key_candidate:
                metadata_by_book[book_id]["keyCandidate"] = key_candidate
            metadata_by_book[book_id].update(edition_evidence(book_id, song_key, edition_additions))
            if source_override and legacy_source_urls:
                metadata_by_book[book_id]["legacySourceUrls"] = [
                    url for url in legacy_source_urls if url not in source_override["sourceUrls"]
                ]
            metadata_by_book[book_id]["keyEvidence"] = key_evidence
            if source_image_url:
                metadata_by_book[book_id]["sourceImageUrl"] = source_image_url
            manifest_entry = remote_entries.get(f"{book_id}/{song_key}")
            if manifest_entry is None and metadata_key != song_key:
                manifest_entry = remote_entries.get(f"{book_id}/{metadata_key}")
            remote_score_key = REMOTE_SCORE_ALIASES.get(book_id, {}).get(song_key, song_key)
            if manifest_entry is None and remote_score_key != song_key:
                manifest_entry = remote_entries.get(f"{book_id}/{remote_score_key}")
            if manifest_entry:
                url = manifest_entry["sourceUrl"]
                source_path = PROJECT_ROOT / manifest_entry["rawPath"]
                cache_key = f"remote:{url}"
            else:
                url = first_matching_url(row)
                source_path = None
                cache_key = f"local:{url}" if url else ""
                # A source URL can be cataloged under another edition's
                # manifest key. Reuse its immutable raw file for parsing, but
                # keep this record's edition provenance separate.
                if url and url in remote_entries_by_url:
                    manifest_entry = remote_entries_by_url[url]
                    source_path = PROJECT_ROOT / manifest_entry["rawPath"]
                    cache_key = f"remote:{url}"
                if not url:
                    url = first_reference_matching_url(row)
                    cache_key = f"local-reference:{url}" if url else ""
                    if url and url in remote_entries_by_url:
                        manifest_entry = remote_entries_by_url[url]
                        source_path = PROJECT_ROOT / manifest_entry["rawPath"]
                        cache_key = f"remote:{url}"
            if manifest_entry and url not in all_source_urls:
                all_source_urls.append(url)
                metadata_by_book[book_id]["sourceUrls"].append(url)

            draft_score = None
            if draft and book_id == "sh2025":
                draft_cache_key = str(draft["artifactPath"])
                if draft_cache_key not in draft_cache:
                    parsed_draft = parse_score(f"draft://{book_id}/{song['songNo']}", draft["artifactPath"])
                    if parsed_draft:
                        detected_key = parsed_draft.get("keySignature", "")
                        source_metadata_key = metadata_by_book[book_id].get("keySignature", "")
                        observed_source_key = source_observed_key(source_metadata_observation)
                        if source_metadata_key:
                            parsed_draft["keySignature"] = source_metadata_key
                            parsed_draft["keyEvidence"] = {
                                "status": "source-verified",
                                "source": metadata_by_book[book_id].get("keyEvidence", {}).get("source", "source metadata"),
                            }
                            annotate_raw_key_conflict(parsed_draft, source_metadata_key)
                            if detected_key and detected_key != source_metadata_key:
                                parsed_draft["omrDetectedKeySignature"] = detected_key
                        elif observed_source_key:
                            parsed_draft["keySignature"] = observed_source_key
                            parsed_draft["keyEvidence"] = {
                                "status": "source-observed",
                                "source": "source image OCR observation; human verification required",
                            }
                            annotate_raw_key_conflict(parsed_draft, observed_source_key)
                            if detected_key and detected_key != observed_source_key:
                                parsed_draft["omrDetectedKeySignature"] = detected_key
                        else:
                            parsed_draft["keySignature"] = detected_key
                            parsed_draft["keyEvidence"] = {
                                "status": "omr-detected" if detected_key else "unknown",
                                "source": "OMR-detected MusicXML key signature" if detected_key else "not detected",
                            }
                        parsed_draft["timeSignature"] = metadata_by_book[book_id].get("timeSignature", "") or parsed_draft.get("timeSignature", "")
                        part_names = ["Treble", "Alto", "Tenor", "Bass"]
                        for index, part in enumerate(parsed_draft["parts"]):
                            part["name"] = part_names[index] if index < len(part_names) else f"Part {index + 1}"
                        draft_cache[draft_cache_key] = parsed_draft
                    else:
                        draft_cache[draft_cache_key] = None
                if draft_cache[draft_cache_key]:
                    draft_score = draft_score_asset(
                        f"{book_id}/{song['songNo']}",
                        draft_cache[draft_cache_key],
                        draft,
                    )
            if not url:
                coverage_record = source_coverage_record(
                    book_id, row, all_source_urls, None, manifest_entry, audit, recording
                )
                coverage_record.update(edition_evidence(book_id, song_key, edition_additions))
                if source_image_url:
                    coverage_record["sourceImageUrl"] = source_image_url
                if draft_score:
                    draft_score_by_book[book_id] = draft_score
                    coverage_record.update({
                        "draftScoreAvailable": True,
                        "draftScoreRef": draft_score["scoreRef"],
                        "draftScoreStatus": "needs-human-review",
                    })
                source_coverage_by_book[book_id] = coverage_record
                if source_coverage_by_book[book_id]["status"] == "transcription-blocked":
                    book_coverage[book_id].setdefault("blockedTranscriptionRecords", 0)
                    book_coverage[book_id]["blockedTranscriptionRecords"] += 1
                elif all_source_urls:
                    book_coverage[book_id]["sourceReferenceRecords"] += 1
                else:
                    book_coverage[book_id]["metadataOnlyRecords"] += 1
                continue
            if cache_key not in score_cache:
                score_cache[cache_key] = parse_score(url, source_path) if source_path and source_path.exists() else existing_score_asset(url)
            if score_cache[cache_key]:
                provenance = score_provenance(book_id, url, manifest_entry)
                # Edition metadata may correct an exact edition source. It
                # must never overwrite the key of an alternate witness whose
                # pitches remain in that witness's original key.
                score_for_asset = (
                    apply_source_key_to_score(score_cache[cache_key], metadata_by_book[book_id])
                    if provenance["kind"] == "edition-source"
                    else score_cache[cache_key]
                )
                score_preview = score_asset(url, score_for_asset, asset_key=f"{book_id}:{url}")
                score_preview["provenance"] = provenance
                if provenance["kind"] == "edition-source":
                    score_by_book[book_id] = score_preview
                    book_coverage[book_id]["localScoreRecords"] += 1
                    book_coverage[book_id]["localScoreParts"] += len(score_cache[cache_key]["parts"])
                else:
                    reference_score_by_book[book_id] = score_preview
            if draft_score:
                draft_score_by_book[book_id] = draft_score
            coverage_record = source_coverage_record(
                book_id,
                row,
                all_source_urls,
                apply_source_key_to_score(score_cache.get(cache_key), metadata_by_book[book_id])
                if cache_key and score_cache.get(cache_key) and score_provenance(book_id, url, manifest_entry)["kind"] == "edition-source"
                else None,
                manifest_entry,
                audit,
                recording,
            )
            coverage_record.update(edition_evidence(book_id, song_key, edition_additions))
            if source_image_url:
                coverage_record["sourceImageUrl"] = source_image_url
            attach_source_metadata_observation(coverage_record, source_metadata_observation)
            attach_clean_source_candidates(coverage_record, clean_source_candidates, book_id, song_key, metadata_key)
            if draft_score:
                coverage_record.update({
                    "draftScoreAvailable": True,
                    "draftScoreRef": draft_score["scoreRef"],
                    "draftScoreStatus": "needs-human-review",
                })
            source_coverage_by_book[book_id] = coverage_record
            status = source_coverage_by_book[book_id]["status"]
            if status == "source-reference":
                book_coverage[book_id]["sourceReferenceRecords"] += 1
            elif status == "metadata-only":
                book_coverage[book_id]["metadataOnlyRecords"] += 1
            elif status == "transcription-blocked":
                book_coverage[book_id].setdefault("blockedTranscriptionRecords", 0)
                book_coverage[book_id]["blockedTranscriptionRecords"] += 1
            score_records[(book_id, song_key)] = book_id in score_by_book
            if metadata_key != song_key:
                score_records[(book_id, metadata_key)] = book_id in score_by_book

        for coverage_book_id, coverage in source_coverage_by_book.items():
            if coverage_book_id == "sh2025":
                observation = source_metadata_observations.get(f"{coverage_book_id}/{str(coverage.get('sourceRecordKey') or song['songNo']).lower()}")
                attach_source_metadata_observation(coverage, observation)
                manifest_audit = shapenote_2025_score_audit.get(
                    f"{coverage_book_id}/{str(coverage.get('sourceRecordKey') or song['songNo']).lower()}"
                )
                if manifest_audit:
                    coverage["manifestScoreAudit"] = {
                        "status": manifest_audit.get("comparisonStatus", ""),
                        "safeToPromote": manifest_audit.get("safeToPromote") is True,
                        "blockedReasons": manifest_audit.get("blockedReasons", []),
                        "sourceSha256": manifest_audit.get("sourceSha256", ""),
                        "externalSourceEvidence": manifest_audit.get("externalSourceEvidence"),
                    }
            attach_clean_source_candidates(
                coverage,
                clean_source_candidates,
                coverage_book_id,
                str(coverage.get("sourceRecordKey") or song["songNo"]).lower(),
                str(song["songNo"]).lower(),
            )
        if source_coverage_by_book:
            enriched["sourceCoverageByBook"] = source_coverage_by_book
            enriched["sourceCoverage"] = source_coverage_by_book.get(song["books"][0]) or next(iter(source_coverage_by_book.values()))
            for coverage_book_id, coverage in source_coverage_by_book.items():
                source_coverage_records.append({
                    "songId": song["id"],
                    "songNo": song["songNo"],
                    "title": song["title"],
                    "bookId": coverage_book_id,
                    **coverage,
                })

        if metadata_by_book:
            enriched["metadataByBook"] = metadata_by_book
            enriched["metadata"] = metadata_by_book.get(song["books"][0]) or next(iter(metadata_by_book.values()))
        if score_by_book:
            enriched["scoreByBook"] = score_by_book
            enriched["score"] = score_by_book.get(song["books"][0]) or next(iter(score_by_book.values()))
            local_scores += 1
            score_parts += sum(len(score["parts"]) for score in score_by_book.values())
        if reference_score_by_book:
            enriched["referenceScoreByBook"] = reference_score_by_book
        if draft_score_by_book:
            enriched["draftScoreByBook"] = draft_score_by_book
        relation = next(
            (
                EXPLICIT_EDITION_RECONCILIATIONS.get((book_id, song["songNo"].lower()))
                or
                edition_relations.get((book_id, song["songNo"].lower()))
                or edition_relations.get((book_id, METADATA_KEY_ALIASES.get(book_id, {}).get(song["songNo"].lower(), "")))
                for book_id in song["books"]
                if book_id in {"sh1991", "sh2025"}
            ),
            None,
        )
        if relation:
            relation_changes = dict(relation.get("changes") or {})
            metadata_differences = source_metadata_differences(metadata_by_book)
            if metadata_differences:
                relation_changes["source_metadata_difference"] = metadata_differences
            enriched["editionReconciliation"] = {
                "books": ["sh1991", "sh2025"],
                "status": "change-flagged" if metadata_differences else relation.get("status", "change-flagged"),
                "relationId": relation["relationId"],
                "relationType": relation["relationType"],
                "records": relation["records"],
                "changes": relation_changes,
            }
        elif "sh1991" in song["books"] and "sh2025" in song["books"]:
            changes = edition_changes.get(song["songNo"].lower(), {})
            # The edition-change CSV records editorial changes such as title
            # and first-line replacements, but it does not carry every
            # source-visible musical field. Surface disagreements in the
            # edition-specific metadata as explicit reconciliation evidence
            # rather than silently classifying the pair as unchanged. This is
            # especially important for a key or mode change: the other
            # edition's MusicXML may remain a useful witness, but it cannot be
            # presented as the selected edition's transposable score.
            metadata_differences = source_metadata_differences(metadata_by_book)
            if metadata_differences:
                changes = dict(changes)
                changes["source_metadata_difference"] = metadata_differences
            relation_records = {}
            for relation_book_id in ("sh1991", "sh2025"):
                relation_metadata = metadata_by_book.get(relation_book_id, {})
                relation_records[relation_book_id] = {
                    "songNo": song["songNo"],
                    "title": song.get("titlesByBook", {}).get(relation_book_id, song["title"]),
                    "url": relation_metadata.get("sourceUrl", "") or next(
                        (url for url in song.get("urls", []) if relation_book_id in url),
                        "",
                    ),
                }
            enriched["editionReconciliation"] = {
                "books": ["sh1991", "sh2025"],
                "status": "change-flagged" if changes else "not-listed-as-changed",
                "relationId": f"sh-edition:{song['songNo'].lower()}",
                "relationType": "shared-record",
                "records": relation_records,
                "changes": changes,
                "scoreAvailability": {
                    book_id: book_id in score_by_book
                    for book_id in ("sh1991", "sh2025")
                },
            }
        songs.append(enriched)

    for song in songs:
        relation = song.get("editionReconciliation")
        if relation and relation.get("relationId"):
            relation["scoreAvailability"] = {
                book_id: score_records.get((book_id, record["songNo"].lower()), False)
                for book_id, record in relation.get("records", {}).items()
            }

    for target in songs:
        target_book_id = "sh2025"
        target_key = target.get("songNo", "").lower()
        source_book_id, source_key = CROSS_EDITION_SCORE_REFERENCES.get((target_book_id, target_key), ("", ""))
        if not source_book_id and {"sh1991", "sh2025"}.issubset(target.get("books", [])):
            source_book_id, source_key = "sh1991", target_key
        source_song = next(
            (
                song for song in songs
                if source_book_id in song.get("books", []) and song.get("songNo", "").lower() == source_key
            ),
            None,
        )
        source_score = (source_song or {}).get("scoreByBook", {}).get(source_book_id)
        if source_score and not target.get("scoreByBook", {}).get(target_book_id):
            reference_score = json.loads(json.dumps(source_score))
            reference_score["provenance"] = {
                "kind": "alternate-source",
                "label": f"Transposable reference · {source_book_id}",
                "sourceEdition": source_book_id,
                "sourceRecordKey": source_key,
            }
            target.setdefault("referenceScoreByBook", {})[target_book_id] = reference_score

    for book_id, coverage in book_coverage.items():
        transposable_records = 0
        transposable_local_scores = 0
        transposable_references = 0
        transposable_drafts = 0
        key_unknown_structured = 0
        for song in songs:
            if book_id not in song.get("books", []):
                continue
            score = song.get("scoreByBook", {}).get(book_id)
            reference = song.get("referenceScoreByBook", {}).get(book_id)
            draft = song.get("draftScoreByBook", {}).get(book_id)
            assets = [asset for asset in (score, reference, draft) if asset]
            if any(asset.get("transposition", {}).get("available") for asset in assets):
                transposable_records += 1
            if score and score.get("transposition", {}).get("available"):
                transposable_local_scores += 1
            if reference and reference.get("transposition", {}).get("available"):
                transposable_references += 1
            if draft and draft.get("transposition", {}).get("available"):
                transposable_drafts += 1
            if assets and not any(asset.get("transposition", {}).get("available") for asset in assets) and any(
                asset.get("transposition", {}).get("hasPitchedEvents") for asset in assets
            ):
                key_unknown_structured += 1
        coverage["transposableRecords"] = transposable_records
        coverage["transposableLocalScoreRecords"] = transposable_local_scores
        coverage["transposableReferenceRecords"] = transposable_references
        coverage["transposableDraftRecords"] = transposable_drafts
        coverage["keyUnknownStructuredRecords"] = key_unknown_structured

    songs_by_id = {song["id"]: song for song in songs}
    transcription_queue: list[dict[str, Any]] = []
    for coverage_record in source_coverage_records:
        if coverage_record["status"] == "structured-score":
            continue
        song = songs_by_id[coverage_record["songId"]]
        metadata_record = song.get("metadataByBook", {}).get(coverage_record["bookId"], {})
        relation = song.get("editionReconciliation")
        transcription_queue.append(
            {
                "queueId": f"{coverage_record['bookId']}/{coverage_record['songNo']}",
                "canonicalRecordId": f"{coverage_record['bookId']}/{coverage_record['songNo']}",
                "songId": coverage_record["songId"],
                "bookId": coverage_record["bookId"],
                "songNo": coverage_record["songNo"],
                "title": coverage_record["title"],
                "status": coverage_record["status"],
                "disposition": transcription_disposition(
                    coverage_record["status"], coverage_record.get("sourceUrls", [])
                ),
                "humanReviewRequired": False,
                "reviewAvailable": bool(coverage_record.get("sourceUrls")),
                "safeToPromote": False,
                "priority": transcription_priority(coverage_record["status"]),
                "nextAction": coverage_record["nextAction"],
                "sourceUrls": coverage_record.get("sourceUrls", []),
                "sourceImageUrl": coverage_record.get("sourceImageUrl", ""),
                "sourceRecordKey": coverage_record.get("sourceRecordKey", ""),
                "editionStatus": coverage_record.get("editionStatus", ""),
                "editionEvidenceUrl": coverage_record.get("editionEvidenceUrl", ""),
                "editionEvidenceLabel": coverage_record.get("editionEvidenceLabel", ""),
                "keySignature": metadata_record.get("keySignature", ""),
                "keyEvidence": metadata_record.get("keyEvidence", {"status": "unknown", "source": "not recorded"}),
                "timeSignature": metadata_record.get("timeSignature", ""),
                "meter": metadata_record.get("meter", ""),
                "composer": metadata_record.get("composer", ""),
                "lyricist": metadata_record.get("lyricist", ""),
                "hasReferenceAudio": bool(coverage_record.get("recordingTracks")),
                "reconciliation": {
                    "status": relation.get("status", "") if relation else "",
                    "relationId": relation.get("relationId", "") if relation else "",
                    "scoreAvailability": relation.get("scoreAvailability", {}) if relation else {},
                },
                "auditStatus": coverage_record.get("auditStatus", ""),
                "transcriptionStatus": coverage_record.get("transcriptionStatus", ""),
                "blockedReason": coverage_record.get("blockedReason", ""),
                "acquisitionNeeded": coverage_record.get("acquisitionNeeded", ""),
                "localArtifacts": coverage_record.get("localArtifacts", {}),
                "cleanSourceCandidates": clean_source_candidates.get(f"{coverage_record['bookId']}/{coverage_record['songNo']}".lower(), []),
            }
        )
    transcription_queue.sort(key=lambda item: (item["priority"], item["bookId"], item["songNo"], item["title"]))

    output = {
        "generatedAt": data.get("generatedAt"),
        "source": {
            "metadataPath": str(SOURCE_DATA),
            "editionChangesPath": str(EDITION_CHANGES),
            "scoreCachePath": str(CACHE_ROOT),
            "policy": "Metadata is retained for every corpus record; score previews appear only for exact local MusicXML mappings.",
        },
        "coverage": {"songs": len(songs), "localScoreSongs": local_scores, "localScoreParts": score_parts, "byBook": book_coverage},
        "books": data["books"],
        "songs": songs,
    }
    if data.get("legacyEditionRecords"):
        output["legacyEditionRecords"] = data["legacyEditionRecords"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    coverage_output = {
        "generatedAt": data.get("generatedAt"),
        "policy": "Each record is classified from current local structured-score data and recorded source references. A source URL is not treated as a verified scan; missing notation remains queued for acquisition or transcription.",
        "summary": {
            "editionRecords": len(source_coverage_records),
            "structuredScores": sum(1 for record in source_coverage_records if record["status"] == "structured-score"),
            "transposableReferenceWitnesses": sum(
                1
                for song in songs
                for book_id in song.get("books", [])
                if song.get("referenceScoreByBook", {}).get(book_id)
            ),
            "sourceReferences": sum(1 for record in source_coverage_records if record["status"] == "source-reference"),
            "metadataOnly": sum(1 for record in source_coverage_records if record["status"] == "metadata-only"),
            "mappingGaps": sum(1 for record in source_coverage_records if record["status"] == "mapping-gap"),
        },
        "records": source_coverage_records,
    }
    (OUTPUT.parent / "source-coverage.json").write_text(
        json.dumps(coverage_output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    queue_by_status: dict[str, int] = {}
    queue_by_book: dict[str, int] = {}
    for item in transcription_queue:
        queue_by_status[item["status"]] = queue_by_status.get(item["status"], 0) + 1
        queue_by_book[item["bookId"]] = queue_by_book.get(item["bookId"], 0) + 1
    TRANSCRIPTION_QUEUE_OUTPUT.write_text(
        json.dumps(
            {
                "generatedAt": data.get("generatedAt"),
                "policy": "Every edition-specific record without an exact structured score is tracked here. Reference audio, scans, and other-edition scores are evidence for future work, never substitutes for the edition's transposable notation.",
                "summary": {
                    "total": len(transcription_queue),
                    "byStatus": queue_by_status,
                    "byBook": queue_by_book,
                },
                "records": transcription_queue,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"Built {OUTPUT} with {len(songs)} songs and {local_scores} full-song MusicXML scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
