#!/usr/bin/env python3
"""Validate spec YAML files under specs/ (id, type, version required)."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED_ROOT = ("id", "type", "version")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: invalid YAML ({exc})"]
    if not isinstance(data, dict):
        return [f"{path}: root must be a mapping"]
    for key in REQUIRED_ROOT:
        if key not in data or data[key] in (None, ""):
            errors.append(f"{path}: missing '{key}'")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "specs"
    if not root.is_dir():
        print(f"No specs directory: {root}", file=sys.stderr)
        return 1
    all_errors: list[str] = []
    for pattern in ("*.yaml", "**/*.yaml"):
        for path in root.glob(pattern):
            if path.is_file():
                all_errors.extend(validate_file(path))
    if all_errors:
        print("\n".join(all_errors), file=sys.stderr)
        return 1
    print(f"OK: validated {len(list(root.rglob('*.yaml')))} spec files under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
