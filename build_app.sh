#!/usr/bin/env bash
# build_app.sh — Bundle gui.py into a macOS .app with PyInstaller
#
# Usage:
#   ./build_app.sh
#
# Output: dist/Photo Location Days.app
# Then zip and upload to GitHub Releases.

set -euo pipefail

echo "==> Installing/upgrading PyInstaller …"
pip install --upgrade pyinstaller

# Find the reverse_geocoder package directory so PyInstaller can bundle its data files
RG_DIR=$(python3 -c "import reverse_geocoder as rg, os; print(os.path.dirname(rg.__file__))")
echo "==> reverse_geocoder found at: $RG_DIR"

echo "==> Building .app …"
pyinstaller \
    --name "Photo Location Days" \
    --windowed \
    --onedir \
    --osx-bundle-identifier "com.photo-location-days" \
    --add-data "${RG_DIR}:reverse_geocoder" \
    --hidden-import osxphotos \
    --hidden-import reverse_geocoder \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk \
    --hidden-import tkinter.scrolledtext \
    --hidden-import tkinter.filedialog \
    gui.py

echo ""
echo "==> Build complete: dist/Photo Location Days.app"
echo ""
echo "Next steps:"
echo "  1. Grant Full Disk Access to the .app in:"
echo "     System Settings → Privacy & Security → Full Disk Access"
echo "  2. Zip for distribution:"
echo "     cd dist && zip -r ../Photo-Location-Days-macOS.zip 'Photo Location Days.app'"
echo "  3. Upload zip to GitHub Releases."
