# photo-location-days — Claude Code context

## What this project does
Reads GPS metadata from a macOS Photos library and counts the number of unique
days the user spent in each US state or country. macOS-only (requires osxphotos).

## Architecture
- **`photo_location_days.py`** — core logic + CLI entry point. Contains all
  data-processing functions (`load_photos`, `build_location_days`,
  `infer_missing_days`, `print_report`) and a `main()` that uses argparse.
  The CLI remains fully functional and unchanged.
- **`gui.py`** — tkinter GUI wrapper. Imports functions directly from
  `photo_location_days.py`, redirects `sys.stdout` to a `ScrolledText` widget
  so the existing `print()` calls appear in the GUI, and runs analysis in a
  background thread to keep the UI responsive.

## Key dependencies
| Package | Purpose |
|---------|---------|
| `osxphotos` | Reads the Photos SQLite database directly (no export needed) |
| `reverse_geocoder` | Offline GPS → country/state lookup (bundles ~25 MB data file) |
| `tkinter` | GUI (ships with Python — no extra install needed) |
| `pytest` | Tests |

## How to run
```bash
# CLI
python3 photo_location_days.py [--library PATH] [--top N] [--group state|country|both] \
                                [--year YYYY] [--sort count|date] [--max-gap DAYS]

# GUI (directly, no build needed)
python3 gui.py
```

## How to build the .app
```bash
./build_app.sh          # produces dist/Photo\ Location\ Days.app
```
Then zip and upload to GitHub Releases:
```bash
cd dist && zip -r ../Photo-Location-Days-macOS.zip "Photo Location Days.app"
gh release create vX.Y.Z --title "vX.Y.Z" --notes "..." Photo-Location-Days-macOS.zip
```

## Testing
```bash
pytest -v
```
All tests use mocks — no osxphotos or reverse_geocoder installation needed for
the test suite.

## Distribution
- `.app` bundle goes on **GitHub Releases** (never committed — ~200-300 MB)
- `dist/` and `build/` are in `.gitignore`

## Full Disk Access
Both the CLI and the `.app` require **Full Disk Access** to read the Photos
library:
> System Settings → Privacy & Security → Full Disk Access

## Personal data policy
No names or email addresses appear in any project files. `LICENSE` uses
"the contributors" rather than any individual name.
