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


def installed_package(name: str) -> tuple[dict[str, object] | None, str | None]:
    package_path = ROOT / "node_modules" / name / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"installed dependency is missing: {name} (run npm ci)"
    except json.JSONDecodeError as error:
        return None, f"installed metadata is malformed for {name}: line {error.lineno}, column {error.colno}"
    except OSError as error:
        return None, f"cannot read installed metadata for {name}: {error}"
    if not isinstance(package, dict):
        return None, f"installed metadata is not an object for {name}"
    version = package.get("version")
    if not isinstance(version, str):
        return None, f"installed metadata has no version for {name}"
    return package, None


def validate_vite_bin(package: dict[str, object]) -> str | None:
    bin_spec = package.get("bin")
    if isinstance(bin_spec, str):
        relative_bin = bin_spec
    elif isinstance(bin_spec, dict) and isinstance(bin_spec.get("vite"), str):
        relative_bin = bin_spec["vite"]
    else:
        return "installed vite metadata has no vite bin declaration"
    package_dir = ROOT / "node_modules" / "vite"
    expected_bin = (package_dir / relative_bin).resolve(strict=False)
    try:
        expected_bin.relative_to(package_dir.resolve())
    except ValueError:
        return f"installed vite bin escapes its package: {relative_bin!r}"
    if not expected_bin.is_file():
        return f"installed vite bin target is missing: {expected_bin}"
    link = ROOT / "node_modules" / ".bin" / "vite"
    if not link.exists() and not link.is_symlink():
        return "local vite executable is missing: node_modules/.bin/vite (run npm ci)"
    resolved_link = link.resolve(strict=False)
    if resolved_link != expected_bin:
        return f"local vite executable resolves to {resolved_link}, expected {expected_bin}"
    return None


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
    installed_versions: dict[str, str] = {}
    installed_packages: dict[str, dict[str, object]] = {}
    for name, requested in sorted(declared.items()):
        entry = packages.get(f"node_modules/{name}")
        if not isinstance(entry, dict) or not isinstance(entry.get("version"), str):
            return fail(f"lockfile has no resolved entry for {name}")
        version = entry["version"]
        resolved[name] = version
        if requested != version:
            return fail(f"{name} requests {requested!r} but lockfile resolves {version!r}")

        installed, error = installed_package(name)
        if error is not None:
            return fail(error)
        assert installed is not None
        installed_version = installed["version"]
        assert isinstance(installed_version, str)
        installed_versions[name] = installed_version
        installed_packages[name] = installed
        if installed_version != version:
            return fail(f"{name} is installed at {installed_version!r} but lockfile resolves {version!r}")

    if "vite" in installed_packages:
        bin_error = validate_vite_bin(installed_packages["vite"])
        if bin_error is not None:
            return fail(bin_error)

    print(
        json.dumps(
            {
                "status": "passed",
                "lockfileVersion": lock.get("lockfileVersion"),
                "resolved": resolved,
                "installed": installed_versions,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
