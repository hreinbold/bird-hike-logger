#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root relative to this script's location, so it works
# regardless of what directory you run it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

source venv/bin/activate

# --- Optional: pull detections.csv from the Pi before processing ----------
# Fill in PI_HOST/PI_PATH and uncomment to enable. Left off by default since
# it depends on your Pi's hostname/path and being reachable on wifi right now.
# PI_HOST="pi@raspberrypi.local"
# PI_PATH="/home/pi/BirdNET-Pi/scripts/detections.csv"
# rsync -av "${PI_HOST}:${PI_PATH}" data/detections/detections.csv

DETECTIONS="data/detections/detections.csv"
NEW_HIKES=0

shopt -s nullglob   # so the loop just does nothing if no .gpx files exist
for gpx in data/gpx/*.gpx; do
    slug=$(basename "$gpx" .gpx | tr '[:upper:]' '[:lower:]' | tr ' _' '-')
    date=$(python scripts/gpx_first_date.py "$gpx")
    out="docs/data/${date}_${slug}.geojson"

    if [ -f "$out" ]; then
        echo "skip: $gpx -> $out already exists"
        continue
    fi

    echo "processing: $gpx -> $out"
    python scripts/merge_detections_gpx.py "$DETECTIONS" "$gpx" "$out"
    NEW_HIKES=$((NEW_HIKES + 1))
done

if [ "$NEW_HIKES" -eq 0 ]; then
    echo "no new hikes to process"
    exit 0
fi

python scripts/build_manifest.py docs/data

# Only committing generated map data -- raw detections.csv and .gpx files
# stay gitignored (they can contain your home location in the track).
git add docs/data

if git diff --cached --quiet; then
    echo "regenerated output is identical to what's already committed -- nothing to push"
    exit 0
fi

git commit -m "Add ${NEW_HIKES} new hike(s)"
git push

echo "done: pushed ${NEW_HIKES} new hike(s)"