#!/usr/bin/env python3
"""Check that the declared frontend dependencies match the retained lockfile.

This is a read-only preflight. It deliberately does not install, upgrade, or
rewrite npm files; ``npm ci`` remains the clean-environment restoration step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(f"dependency preflight failed: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        return fail(f"missing {error.filename}")
    except json.JSONDecodeError as error:
        return fail(f"malformed JSON at line {error.lineno}, column {error.colno}")
    except OSError as error:
        return fail(str(error))

    declared = package.get("dependencies")
    root_package = lock.get("packages", {}).get("")
    locked = root_package.get("dependencies") if isinstance(root_package, dict) else None
    if not isinstance(declared, dict) or not isinstance(locked, dict):
        return fail("package.json dependencies or package-lock root dependencies are missing")
    if declared != locked:
        return fail(f"package.json and package-lock.json disagree: declared={declared!r} locked={locked!r}")

    packages = lock.get("packages")
    if not isinstance(packages, dict):
        return fail("package-lock.json packages table is missing")
    resolved: dict[str, str] = {}
    for name, requested in sorted(declared.items()):
        entry = packages.get(f"node_modules/{name}")
        if not isinstance(entry, dict) or not isinstance(entry.get("version"), str):
            return fail(f"lockfile has no resolved entry for {name}")
        version = entry["version"]
        resolved[name] = version
        if requested != version:
            return fail(f"{name} requests {requested!r} but lockfile resolves {version!r}")

    print(json.dumps({"status": "passed", "lockfileVersion": lock.get("lockfileVersion"), "resolved": resolved}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
