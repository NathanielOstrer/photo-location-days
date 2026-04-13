#!/usr/bin/env python3
"""
gui.py — tkinter GUI wrapper for photo_location_days.py

Run directly:  python3 gui.py
Build .app:    ./build_app.sh
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

from photo_location_days import (
    load_photos,
    build_location_days,
    infer_missing_days,
    print_report,
)


class StdoutRedirector:
    """Redirect writes to a tkinter ScrolledText widget (thread-safe)."""

    def __init__(self, widget, root):
        self.widget = widget
        self.root = root

    def write(self, text):
        self.root.after(0, self._append, text)

    def _append(self, text):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Location Days")
        self.resizable(True, True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Top-level layout ──────────────────────────────────────────
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="ns")

        right = ttk.Frame(self, padding=(0, 12, 12, 12))
        right.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Left panel controls ───────────────────────────────────────
        row = 0

        # Library path
        ttk.Label(left, text="Library path:").grid(row=row, column=0, columnspan=2,
                                                    sticky="w", pady=(0, 2))
        row += 1
        self._library_var = tk.StringVar()
        lib_entry = ttk.Entry(left, textvariable=self._library_var, width=32)
        lib_entry.grid(row=row, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(left, text="Browse…", command=self._browse_library).grid(
            row=row, column=1, sticky="w")
        left.columnconfigure(0, weight=1)
        row += 1

        ttk.Separator(left, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        # Group by
        ttk.Label(left, text="Group by:").grid(row=row, column=0, sticky="w")
        self._group_var = tk.StringVar(value="state")
        ttk.Combobox(left, textvariable=self._group_var,
                     values=["state", "country", "both"],
                     state="readonly", width=12).grid(row=row, column=1, sticky="w")
        row += 1

        # Sort by
        ttk.Label(left, text="Sort by:").grid(row=row, column=0, sticky="w", pady=(6, 0))
        self._sort_var = tk.StringVar(value="count")
        ttk.Combobox(left, textvariable=self._sort_var,
                     values=["count", "date"],
                     state="readonly", width=12).grid(row=row, column=1, sticky="w",
                                                       pady=(6, 0))
        row += 1

        # Year
        ttk.Label(left, text="Year:").grid(row=row, column=0, sticky="w", pady=(6, 0))
        self._year_var = tk.StringVar(value="")
        year_spin = ttk.Spinbox(left, textvariable=self._year_var,
                                from_=2000, to=2035, width=8,
                                increment=1)
        year_spin.set("")
        year_spin.grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        # Top N
        ttk.Label(left, text="Top N:").grid(row=row, column=0, sticky="w", pady=(6, 0))
        self._top_var = tk.StringVar(value="")
        top_spin = ttk.Spinbox(left, textvariable=self._top_var,
                               from_=1, to=999, width=8, increment=1)
        top_spin.set("")
        top_spin.grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        # Max gap
        ttk.Label(left, text="Max gap (days):").grid(row=row, column=0, sticky="w",
                                                     pady=(6, 0))
        self._max_gap_var = tk.StringVar(value="7")
        ttk.Spinbox(left, textvariable=self._max_gap_var,
                    from_=0, to=365, width=8, increment=1).grid(
            row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Separator(left, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self._run_btn = ttk.Button(btn_frame, text="Run", command=self._run)
        self._run_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btn_frame, text="Clear", command=self._clear_output).pack(
            side="left", expand=True, fill="x")

        # ── Right panel — output text area ────────────────────────────
        self._output = scrolledtext.ScrolledText(
            right, state="disabled", wrap="none",
            font=("Menlo", 11), width=80, height=30)
        self._output.pack(fill="both", expand=True)

        # Redirect stdout to the text widget
        self._redirector = StdoutRedirector(self._output, self)
        sys.stdout = self._redirector

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_library(self):
        path = filedialog.askdirectory(
            title="Select .photoslibrary folder",
            mustexist=True,
        )
        if path:
            self._library_var.set(path)

    def _clear_output(self):
        self._output.configure(state="normal")
        self._output.delete("1.0", tk.END)
        self._output.configure(state="disabled")

    def _run(self):
        self._run_btn.configure(state="disabled")
        self._clear_output()
        threading.Thread(target=self._analysis_thread, daemon=True).start()

    def _analysis_thread(self):
        try:
            library = self._library_var.get().strip() or None
            group_by = self._group_var.get()
            sort_by = self._sort_var.get()

            year_raw = self._year_var.get().strip()
            year = int(year_raw) if year_raw else None

            top_raw = self._top_var.get().strip()
            top = int(top_raw) if top_raw else None

            max_gap_raw = self._max_gap_var.get().strip()
            max_gap = int(max_gap_raw) if max_gap_raw else 7

            print("Loading Photos library …")
            photos = load_photos(library)
            location_days = build_location_days(photos, group_by=group_by, year=year)
            if max_gap > 0:
                location_days = infer_missing_days(location_days, max_gap=max_gap)
            print_report(location_days, top=top, group_by=group_by, sort_by=sort_by)

        except Exception as exc:
            print(f"\nError: {exc}")
            if "Full Disk Access" in str(exc) or "permission" in str(exc).lower():
                print("\nGrant Full Disk Access to this app in:")
                print("  System Settings → Privacy & Security → Full Disk Access")
        finally:
            self.after(0, lambda: self._run_btn.configure(state="normal"))


def main():
    app = App()
    app.mainloop()
    # Restore stdout when the window closes
    sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
