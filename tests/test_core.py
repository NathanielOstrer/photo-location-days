"""Tests for photo_location_days core logic.

All tests use mock data — no osxphotos or reverse_geocoder imports needed.
"""

import sys
import os
import io
from datetime import date
from unittest.mock import patch

# Make the parent directory importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from photo_location_days import (
    _country_name,
    _split_spans,
    build_location_days,
    infer_missing_days,
    print_report,
)


# ---------------------------------------------------------------------------
# _country_name
# ---------------------------------------------------------------------------

class TestCountryName:
    def test_known_us(self):
        assert _country_name("US") == "United States"

    def test_known_jp(self):
        assert _country_name("JP") == "Japan"

    def test_unknown_passthrough(self):
        assert _country_name("XX") == "XX"

    def test_empty_string(self):
        assert _country_name("") == ""

    def test_none(self):
        assert _country_name(None) == ""


# ---------------------------------------------------------------------------
# _split_spans
# ---------------------------------------------------------------------------

class TestSplitSpans:
    def test_empty(self):
        assert _split_spans(set()) == []

    def test_single_day(self):
        d = date(2024, 6, 1)
        assert _split_spans({d}) == [[d]]

    def test_contiguous_block(self):
        days = {date(2024, 6, 1), date(2024, 6, 2), date(2024, 6, 3)}
        result = _split_spans(days)
        assert len(result) == 1
        assert result[0] == [date(2024, 6, 1), date(2024, 6, 2), date(2024, 6, 3)]

    def test_two_separate_spans(self):
        days = {date(2024, 6, 1), date(2024, 6, 2), date(2024, 6, 10), date(2024, 6, 11)}
        result = _split_spans(days)
        assert len(result) == 2
        assert result[0] == [date(2024, 6, 1), date(2024, 6, 2)]
        assert result[1] == [date(2024, 6, 10), date(2024, 6, 11)]

    def test_scattered_days(self):
        days = {date(2024, 1, 1), date(2024, 3, 5), date(2024, 7, 20)}
        result = _split_spans(days)
        assert len(result) == 3
        assert all(len(span) == 1 for span in result)


# ---------------------------------------------------------------------------
# Helpers for build_location_days tests
# ---------------------------------------------------------------------------

class FakeDate:
    """Wraps a date object to mimic osxphotos photo.date (has .year and .date())."""
    def __init__(self, d: date):
        self._d = d
        self.year = d.year

    def date(self):
        return self._d


class FakePhoto:
    def __init__(self, lat, lon, d):
        self.location = (lat, lon) if lat is not None else None
        self.date = FakeDate(d) if d is not None else None


def make_geo(cc="US", admin1="California", name="Los Angeles"):
    return {"cc": cc, "admin1": admin1, "name": name}


# ---------------------------------------------------------------------------
# build_location_days
# ---------------------------------------------------------------------------

class TestBuildLocationDays:
    def _run(self, photos, geo_results, **kwargs):
        with patch("photo_location_days.geocode_batch", return_value=geo_results):
            return build_location_days(photos, **kwargs)

    def test_state_grouping(self, capsys):
        photos = [
            FakePhoto(34.05, -118.24, date(2024, 6, 1)),  # LA
            FakePhoto(37.77, -122.41, date(2024, 6, 2)),  # SF
        ]
        geo = [make_geo("US", "California"), make_geo("US", "California")]
        result = self._run(photos, geo, group_by="state")
        assert "California" in result
        assert date(2024, 6, 1) in result["California"]
        assert date(2024, 6, 2) in result["California"]

    def test_country_grouping(self, capsys):
        photos = [
            FakePhoto(35.68, 139.69, date(2024, 8, 1)),  # Tokyo
        ]
        geo = [make_geo("JP", "Tokyo", "Tokyo")]
        result = self._run(photos, geo, group_by="country")
        assert "Japan" in result

    def test_both_grouping(self, capsys):
        photos = [FakePhoto(34.05, -118.24, date(2024, 6, 1))]
        geo = [make_geo("US", "California")]
        result = self._run(photos, geo, group_by="both")
        assert "California" in result
        assert "United States" in result

    def test_year_filter(self, capsys):
        photos = [
            FakePhoto(34.05, -118.24, date(2023, 1, 1)),
            FakePhoto(34.05, -118.24, date(2024, 1, 1)),
        ]
        geo = [make_geo("US", "California")]
        result = self._run(photos, geo, group_by="state", year=2024)
        assert "California" in result
        assert date(2023, 1, 1) not in result["California"]
        assert date(2024, 1, 1) in result["California"]

    def test_none_location_skipped(self, capsys):
        photos = [FakePhoto(None, None, date(2024, 6, 1))]
        result = self._run(photos, [], group_by="state")
        assert result == {}

    def test_none_date_skipped(self, capsys):
        p = FakePhoto(34.05, -118.24, None)
        p.date = None
        result = self._run([p], [], group_by="state")
        assert result == {}

    def test_empty_cc_skipped(self, capsys):
        photos = [FakePhoto(34.05, -118.24, date(2024, 6, 1))]
        geo = [{"cc": "", "admin1": "Somewhere", "name": "Place"}]
        result = self._run(photos, geo, group_by="state")
        assert result == {}


# ---------------------------------------------------------------------------
# infer_missing_days
# ---------------------------------------------------------------------------

class TestInferMissingDays:
    def test_gap_filled(self):
        loc_days = {"Texas": {date(2024, 6, 1), date(2024, 6, 4)}}
        result = infer_missing_days(loc_days, max_gap=7)
        assert date(2024, 6, 2) in result["Texas"]
        assert date(2024, 6, 3) in result["Texas"]

    def test_gap_too_large_not_filled(self):
        loc_days = {"Texas": {date(2024, 6, 1), date(2024, 6, 10)}}
        result = infer_missing_days(loc_days, max_gap=7)
        # gap = 9 days > max_gap=7, should not fill
        assert date(2024, 6, 5) not in result["Texas"]

    def test_conflicting_location_not_filled(self):
        loc_days = {
            "Texas": {date(2024, 6, 1), date(2024, 6, 5)},
            "California": {date(2024, 6, 3)},
        }
        result = infer_missing_days(loc_days, max_gap=7)
        # June 3 is occupied by California, so Texas gap should not be filled
        assert date(2024, 6, 2) not in result["Texas"]

    def test_adjacent_days_unchanged(self):
        original = {date(2024, 6, 1), date(2024, 6, 2)}
        loc_days = {"Texas": set(original)}
        result = infer_missing_days(loc_days, max_gap=7)
        assert result["Texas"] == original

    def test_empty_input(self):
        assert infer_missing_days({}) == {}

    def test_single_day_unchanged(self):
        loc_days = {"Texas": {date(2024, 6, 1)}}
        result = infer_missing_days(loc_days, max_gap=7)
        assert result["Texas"] == {date(2024, 6, 1)}


# ---------------------------------------------------------------------------
# print_report
# ---------------------------------------------------------------------------

class TestPrintReport:
    def _capture(self, *args, **kwargs):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            print_report(*args, **kwargs)
        return buf.getvalue()

    def test_sort_by_count(self):
        data = {
            "Texas": {date(2024, 1, i) for i in range(1, 11)},   # 10 days
            "California": {date(2024, 2, i) for i in range(1, 4)},  # 3 days
        }
        output = self._capture(data, sort_by="count")
        lines = [l for l in output.splitlines() if l.strip() and not l.startswith("-")]
        # First data row should be Texas (more days)
        data_rows = [l for l in lines if l[0].isdigit()]
        assert "Texas" in data_rows[0]
        assert "California" in data_rows[1]

    def test_sort_by_date(self):
        data = {
            "Texas": {date(2024, 3, 1)},
            "California": {date(2024, 1, 1)},
        }
        output = self._capture(data, sort_by="date")
        lines = [l for l in output.splitlines() if l[0:1].isdigit()] if output else []
        data_rows = [l for l in output.splitlines() if l and l[0].isdigit()]
        assert "California" in data_rows[0]
        assert "Texas" in data_rows[1]

    def test_top_limits_output(self):
        data = {
            "A": {date(2024, 1, i) for i in range(1, 6)},
            "B": {date(2024, 2, i) for i in range(1, 4)},
            "C": {date(2024, 3, 1)},
        }
        output = self._capture(data, top=2, sort_by="count")
        data_rows = [l for l in output.splitlines() if l and l[0].isdigit()]
        assert len(data_rows) == 2

    def test_empty_input(self):
        output = self._capture({})
        assert "No location data" in output
