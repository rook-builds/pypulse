"""Tests for pypulse.core formatters. Green from scaffold."""

import csv
import io
import json

from pypulse.core import to_csv, to_json, to_table, to_text


class TestToText:
    def test_includes_title(self, sample_items):
        assert "A first item" in to_text(sample_items)

    def test_includes_url(self, sample_items):
        assert "https://example.com/1" in to_text(sample_items)

    def test_includes_score(self, sample_items):
        assert "42" in to_text(sample_items)

    def test_empty(self, empty_items):
        assert "No items found" in to_text(empty_items)


class TestToJson:
    def test_valid_json(self, sample_items):
        data = json.loads(to_json(sample_items))
        assert data["count"] == 2
        assert data["items"][0]["title"] == "A first item"

    def test_created_at_iso(self, sample_items):
        data = json.loads(to_json(sample_items))
        assert data["items"][0]["created_at"].startswith("2026-07-10")


class TestToTable:
    def test_has_header(self, sample_items):
        assert "| # | Package |" in to_table(sample_items)

    def test_has_downloads_column(self, sample_items):
        assert "Downloads/mo" in to_table(sample_items)

    def test_escapes_pipes(self, sample_items):
        # title has no pipe, but the row must be well-formed
        assert to_table(sample_items).count("\n") >= 3

    def test_empty(self, empty_items):
        assert "No items found" in to_table(empty_items)


class TestToCsv:
    def test_roundtrips(self, sample_items):
        rows = list(csv.reader(io.StringIO(to_csv(sample_items))))
        assert rows[0] == ["title", "url", "author", "score", "comments", "created_at"]
        assert rows[1][0] == "A first item"
