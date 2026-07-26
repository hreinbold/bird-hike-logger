#!/usr/bin/env python3
"""Print the UTC date (YYYY-MM-DD) of a GPX track's first point."""

import sys
import gpxpy


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} track.gpx", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        gpx = gpxpy.parse(f)

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                print(point.time.strftime("%Y-%m-%d"))
                return

    print("no track points found in file", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
