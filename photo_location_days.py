#!/usr/bin/env python3
"""
photo_location_days.py
Reads GPS metadata from your Photos library and counts the number of unique
days you were in each state/country.

Requirements:
  osxphotos        — reads macOS Photos library metadata
  reverse_geocoder — offline GPS → state/country lookup

Usage:
  python3 photo_location_days.py
  python3 photo_location_days.py --library "/path/to/Custom.photoslibrary"
  python3 photo_location_days.py --top 20          # show top 20 locations
  python3 photo_location_days.py --group country   # group by country only
"""

import sys
import argparse
from collections import defaultdict
from datetime import date


def load_photos(library_path=None):
    import osxphotos

    if library_path:
        db = osxphotos.PhotosDB(library_path)
    else:
        db = osxphotos.PhotosDB()

    photos = db.photos()
    print(f"Found {len(photos):,} total photos/videos in library.")
    return photos


def geocode_batch(coords):
    """Reverse-geocode a list of (lat, lon) tuples. Returns list of result dicts."""
    import reverse_geocoder as rg
    return rg.search(coords, mode=1, verbose=False)  # mode=1 = faster single-thread


def build_location_days(photos, group_by="state", year=None):
    """
    Returns a dict: location_name -> set of date objects.
    group_by: "state" | "country" | "both"
    year: int or None — if set, only include photos from that year
    """
    # Collect photos that have GPS + date
    gps_photos = []
    for p in photos:
        if p.location and p.date:
            if year and p.date.year != year:
                continue
            lat, lon = p.location
            if lat is not None and lon is not None:
                gps_photos.append((p, lat, lon))

    print(f"{len(gps_photos):,} photos have GPS coordinates.")
    if not gps_photos:
        print("No GPS data found. Make sure your Photos library is accessible.")
        return {}

    # Batch geocode
    print("Reverse-geocoding coordinates (offline) …")
    coords = [(lat, lon) for _, lat, lon in gps_photos]
    results = geocode_batch(coords)

    # Build location → days mapping
    location_days = defaultdict(set)
    skipped = 0

    for (photo, _, _), geo in zip(gps_photos, results):
        cc = geo.get("cc", "").strip()        # ISO country code e.g. "US"
        name = geo.get("name", "").strip()    # city/place name
        admin1 = geo.get("admin1", "").strip()  # state / region
        country = _country_name(cc)

        if not country:
            skipped += 1
            continue

        if group_by == "country":
            location_label = country
        elif group_by == "state":
            if cc == "US" and admin1:
                location_label = admin1
            elif admin1:
                location_label = f"{admin1}, {country}"
            else:
                location_label = country
        else:  # "both" — keep state and country separate
            if cc == "US" and admin1:
                location_days[admin1].add(photo.date.date())
            if country:
                location_days[country].add(photo.date.date())
            continue

        location_days[location_label].add(photo.date.date())

    if skipped:
        print(f"  (skipped {skipped} photos with unresolvable location)")

    return location_days


def infer_missing_days(location_days, max_gap=7):
    """
    Fill gaps in the timeline by extrapolation.
    If the same location bookends a gap of <= max_gap days with no conflicting
    data from a different location, fill those days in.
    """
    from datetime import timedelta

    # Master map of date -> set of locations (from real data only)
    date_to_locs = defaultdict(set)
    for loc, days in location_days.items():
        for d in days:
            date_to_locs[d].add(loc)

    inferred = defaultdict(set)
    for loc, days in location_days.items():
        sorted_days = sorted(days)
        for i in range(len(sorted_days) - 1):
            d1, d2 = sorted_days[i], sorted_days[i + 1]
            gap = (d2 - d1).days
            if gap <= 1 or gap > max_gap:
                continue
            gap_days = [d1 + timedelta(days=j) for j in range(1, gap)]
            # Skip if any gap day already has a *different* location recorded
            if any(date_to_locs.get(gd, set()) - {loc} for gd in gap_days):
                continue
            for gd in gap_days:
                inferred[loc].add(gd)

    total = sum(len(d) for d in inferred.values())
    if total:
        print(f"  Inferred {total} additional day(s) by gap-filling (max gap: {max_gap}d).")

    result = {loc: set(days) for loc, days in location_days.items()}
    for loc, days in inferred.items():
        result[loc].update(days)
    return result


def _country_name(cc):
    """Map ISO-2 country code to a readable name for common countries."""
    _MAP = {
        "US": "United States", "GB": "United Kingdom", "CA": "Canada",
        "AU": "Australia", "FR": "France", "DE": "Germany", "IT": "Italy",
        "ES": "Spain", "JP": "Japan", "CN": "China", "MX": "Mexico",
        "BR": "Brazil", "IN": "India", "NZ": "New Zealand", "PT": "Portugal",
        "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland",
        "AT": "Austria", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
        "FI": "Finland", "IE": "Ireland", "PL": "Poland", "CZ": "Czech Republic",
        "GR": "Greece", "TR": "Turkey", "ZA": "South Africa", "AR": "Argentina",
        "CL": "Chile", "CO": "Colombia", "PE": "Peru", "TH": "Thailand",
        "VN": "Vietnam", "ID": "Indonesia", "PH": "Philippines", "SG": "Singapore",
        "MY": "Malaysia", "HK": "Hong Kong", "TW": "Taiwan", "KR": "South Korea",
        "IL": "Israel", "AE": "UAE", "EG": "Egypt", "MA": "Morocco",
        "KE": "Kenya", "NG": "Nigeria", "TZ": "Tanzania",
        "IS": "Iceland", "HR": "Croatia", "HU": "Hungary", "RO": "Romania",
        "UA": "Ukraine", "RU": "Russia", "CU": "Cuba", "JM": "Jamaica",
        "DO": "Dominican Republic", "PR": "Puerto Rico", "CR": "Costa Rica",
        "PA": "Panama", "GT": "Guatemala", "EC": "Ecuador", "BO": "Bolivia",
        "UY": "Uruguay", "PY": "Paraguay", "VE": "Venezuela",
    }
    return _MAP.get(cc, cc) if cc else ""


def _split_spans(days):
    """Split a set of dates into contiguous runs. Returns list of lists."""
    from datetime import timedelta
    if not days:
        return []
    sorted_days = sorted(days)
    spans, current = [], [sorted_days[0]]
    for d in sorted_days[1:]:
        if (d - current[-1]).days == 1:
            current.append(d)
        else:
            spans.append(current)
            current = [d]
    spans.append(current)
    return spans


def print_report(location_days, top=None, group_by="state", sort_by="count"):
    if not location_days:
        print("\nNo location data to report.")
        return

    label = {"state": "State / Region", "country": "Country", "both": "Location"}[group_by]
    total_located_days = len(set(d for days in location_days.values() for d in days))

    print()

    if sort_by == "date":
        # Expand each location into individual spans, then sort all spans by start date
        rows = []
        for loc, days in location_days.items():
            for span in _split_spans(days):
                rows.append((loc, span))
        rows.sort(key=lambda x: x[1][0])
        if top:
            rows = rows[:top]

        print(f"{'#':<5}  {label:<35}  {'Days':>6}  Date range")
        print("-" * 75)
        for i, (loc, span) in enumerate(rows, 1):
            first = span[0].strftime("%b %-d")
            last  = span[-1].strftime("%b %-d")
            date_range = first if first == last else f"{first} – {last}"
            print(f"{i:<5}  {loc:<35}  {len(span):>6}  {date_range}")

    else:
        ranked = sorted(location_days.items(), key=lambda x: len(x[1]), reverse=True)
        if top:
            ranked = ranked[:top]

        print(f"{'#':<5}  {label:<35}  {'Days':>6}  Date range")
        print("-" * 75)
        for i, (loc, days) in enumerate(ranked, 1):
            sorted_days = sorted(days)
            first = sorted_days[0].strftime("%b %-d")
            last  = sorted_days[-1].strftime("%b %-d")
            date_range = first if first == last else f"{first} – {last}"
            print(f"{i:<5}  {loc:<35}  {len(days):>6}  {date_range}")

    print("-" * 75)
    print(f"       {'Total unique located days':<35}  {total_located_days:>6}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--library", metavar="PATH",
                        help="Path to .photoslibrary (default: system Photos library)")
    parser.add_argument("--top", type=int, default=None,
                        help="Show only top N locations (default: all)")
    parser.add_argument("--group", choices=["state", "country", "both"],
                        default="state",
                        help="Group by state/region (default), country, or both")
    parser.add_argument("--year", type=int, default=None,
                        help="Filter to a specific year, e.g. --year 2026")
    parser.add_argument("--sort", choices=["count", "date"], default="count",
                        help="Sort by day count (default) or chronological first appearance")
    parser.add_argument("--max-gap", type=int, default=7, metavar="DAYS",
                        help="Max gap (days) to fill by extrapolation (default: 7, set 0 to disable)")
    args = parser.parse_args()

    print("Loading Photos library …")
    try:
        photos = load_photos(args.library)
    except Exception as e:
        print(f"\nError opening library: {e}")
        print("\nIf you see a permissions error, grant Full Disk Access to Terminal:")
        print("  System Settings → Privacy & Security → Full Disk Access → enable Terminal")
        sys.exit(1)

    location_days = build_location_days(photos, group_by=args.group, year=args.year)
    if args.max_gap > 0:
        location_days = infer_missing_days(location_days, max_gap=args.max_gap)
    print_report(location_days, top=args.top, group_by=args.group, sort_by=args.sort)


if __name__ == "__main__":
    main()
