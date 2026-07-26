#!/usr/bin/env python3
"""
Scan docs/data/*.geojson (named YYYY-MM-DD_slug-name.geojson) and build
docs/data/manifest.json listing all available hikes for the map page's
hike switcher.

Usage:
    python build_manifest.py docs/data
"""

import sys
import json
import re
from pathlib import Path

FILENAME_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)\.geojson$")


def label_from_slug(slug):
    return slug.replace("-", " ").replace("_", " ").title()


def build_entry(path):
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        print(f"skipping {path.name}: doesn't match YYYY-MM-DD_slug.geojson")
        return None

    date, slug = match.groups()

    with open(path) as f:
        data = json.load(f)
    detection_count = sum(
        1 for feat in data["features"]
        if feat["properties"].get("feature_type") == "detection"
    )

    return {
        "id": path.stem,
        "date": date,
        "label": label_from_slug(slug),
        "file": f"data/{path.name}",
        "detection_count": detection_count,
    }


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} docs/data")
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    entries = []
    for path in sorted(data_dir.glob("*.geojson")):
        entry = build_entry(path)
        if entry:
            entries.append(entry)

    entries.sort(key=lambda e: e["date"], reverse=True)

    out_path = data_dir / "manifest.json"
    with open(out_path, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"wrote {len(entries)} hike(s) to {out_path}")


if __name__ == "__main__":
    main()
