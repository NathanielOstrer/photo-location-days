# photo-location-days

Count the number of days you spent in each US state or country, using GPS metadata from your macOS Photos library.

## What it does

`photo_location_days.py` reads every photo and video in your Photos library, extracts GPS coordinates, reverse-geocodes them offline (no API key needed), and produces a ranked table like:

```
#      State / Region                       Days  Date range
---------------------------------------------------------------------------
1      California                             42  Jan 1 – Dec 28
2      New York                               18  Mar 3 – Nov 14
3      Texas                                   9  Feb 10 – Oct 5
...
```

It can also fill short gaps in the timeline (e.g. if you were in California on the 1st and 4th but have no photos on the 2nd–3rd, it infers you stayed put).

## How it works

- **[osxphotos](https://github.com/RhetTbull/osxphotos)** reads the Photos SQLite database directly — no export needed.
- **[reverse_geocoder](https://github.com/thampiman/reverse-geocoder)** resolves coordinates to country/state offline using a bundled dataset.

## Requirements

- macOS (Photos library required)
- Python 3.10+
- **Full Disk Access** granted to your terminal app
  *(System Settings → Privacy & Security → Full Disk Access)*

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/photo-location-days.git
cd photo-location-days
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Basic — group by US state / region, show all locations
python3 photo_location_days.py

# Use a specific Photos library
python3 photo_location_days.py --library "/Volumes/External/My.photoslibrary"

# Show only the top 20 locations
python3 photo_location_days.py --top 20

# Group by country instead of state
python3 photo_location_days.py --group country

# Show both state and country entries
python3 photo_location_days.py --group both

# Filter to a single year
python3 photo_location_days.py --year 2024

# Sort chronologically instead of by day count
python3 photo_location_days.py --sort date

# Disable gap-filling
python3 photo_location_days.py --max-gap 0

# Increase gap-fill window to 14 days
python3 photo_location_days.py --max-gap 14
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--library PATH` | system library | Path to a `.photoslibrary` |
| `--top N` | all | Show only the top N locations |
| `--group` | `state` | `state`, `country`, or `both` |
| `--year YYYY` | all years | Filter to a specific year |
| `--sort` | `count` | `count` (most days first) or `date` (chronological) |
| `--max-gap DAYS` | `7` | Gap-fill window in days; `0` to disable |

## GUI App

### Run directly (no build needed)

```bash
python3 gui.py
```

A window opens with fields for all CLI options. Results appear in the text area as the analysis runs.

### Build a standalone macOS .app

```bash
./build_app.sh
```

This uses PyInstaller to produce `dist/Photo Location Days.app`. After building:

1. **Grant Full Disk Access** to the `.app` in:
   System Settings → Privacy & Security → Full Disk Access
2. Launch `dist/Photo Location Days.app` directly — no Python installation required.

> The `.app` bundle is ~200-300 MB and is distributed via GitHub Releases, not committed to the repository.

## Running tests

```bash
pip install pytest
pytest -v
```

## Disclaimer

This tool is provided as-is, with no warranty of any kind. The author(s) are not responsible for any issues arising from its use. It is shared in the hope that it will be useful. Use at your own risk.

## License

MIT — see [LICENSE](LICENSE).
