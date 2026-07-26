#!/usr/bin/env python3
"""
Merge BirdNET-Pi mobile-logger detections with a Strava GPX track,
matching each detection to the nearest-in-time GPS point.

Usage:
    python merge_detections_gpx.py detections.csv hike.gpx output.geojson
"""

import sys
import json
import pandas as pd
import gpxpy

# --- Config -----------------------------------------------------------
# No confidence threshold here on purpose -- filtering by confidence happens
# client-side in the map page (a slider over properties.confidence), so the
# geojson keeps every bird detection and the frontend decides what to show.
# Non-bird classes BirdNET's model can emit -- these are not species detections
NON_BIRD_CLASSES = {
    "Power tools", "Human vocal", "Human non-vocal", "Human whistle",
    "Environmental noise", "Engine", "Siren", "Dog", "Gun", "Fireworks",
}
# If a detection's nearest GPS point is farther than this in time, drop it
# rather than snapping it to a wildly wrong location (e.g. before hike start).
MAX_TIME_GAP = pd.Timedelta(minutes=2)


def load_detections(path):
    df = pd.read_csv(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    before = len(df)
    df = df[~df["common_name"].isin(NON_BIRD_CLASSES)]
    print(f"detections: {before} raw -> {len(df)} after removing non-bird classes")

    # merge_asof requires the join key to be sorted
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def load_gpx_track(path):
    with open(path) as f:
        gpx = gpxpy.parse(f)

    points = [
        {"timestamp_utc": p.time, "lat": p.latitude, "lon": p.longitude,
         "elevation": p.elevation}
        for track in gpx.tracks
        for segment in track.segments
        for p in segment.points
    ]
    df = pd.DataFrame(points)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    print(f"gpx track points: {len(df)}")

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def merge_nearest(detections, track):
    # This is the key idiom: merge_asof is a "nearest (or forward/backward)
    # timestamp join" -- there's no direct NCL/bash equivalent, but it's
    # the same idea as manually walking two sorted arrays with two pointers.
    merged = pd.merge_asof(
        detections,
        track,
        on="timestamp_utc",
        direction="nearest",
        tolerance=MAX_TIME_GAP,
    )

    unmatched = merged["lat"].isna().sum()
    if unmatched:
        print(f"warning: {unmatched} detections had no GPS point within {MAX_TIME_GAP}, dropping")
    merged = merged.dropna(subset=["lat", "lon"])

    return merged


def route_feature(track):
    # One LineString feature representing the full hike path -- this is what
    # the map page draws as the route line, separate from the detection points.
    coords = list(zip(track["lon"], track["lat"]))
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "feature_type": "route",
            "start_time_utc": track["timestamp_utc"].iloc[0].isoformat(),
            "end_time_utc": track["timestamp_utc"].iloc[-1].isoformat(),
        },
    }


def to_geojson(merged, track):
    features = [route_feature(track)]
    for _, row in merged.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["lon"], row["lat"]],
            },
            "properties": {
                "feature_type": "detection",
                "species": row["common_name"],
                "scientific_name": row["scientific_name"],
                "confidence": round(float(row["confidence"]), 3),
                "timestamp_utc": row["timestamp_utc"].isoformat(),
                "source_wav": row["source_wav"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def main():
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} detections.csv hike.gpx output.geojson")
        sys.exit(1)

    detections_path, gpx_path, out_path = sys.argv[1:4]

    detections = load_detections(detections_path)
    track = load_gpx_track(gpx_path)
    merged = merge_nearest(detections, track)

    geojson = to_geojson(merged, track)
    with open(out_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"wrote {len(geojson['features'])} detection points to {out_path}")


if __name__ == "__main__":
    main()
