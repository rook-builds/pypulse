"""Tests for pypulse.core.fetch() — all external calls mocked."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
import types

import pytest

from pypulse.core import fetch, Item


# ---------------------------------------------------------------------------
# Helpers — build mock HTTP responses
# ---------------------------------------------------------------------------

def _pypi_json(name: str, version: str = "1.0.0", author: str = "testuser") -> dict:
    return {
        "info": {"version": version, "author": author},
        "releases": {
            version: [{"upload_time_iso_8601": "2026-08-01T12:00:00Z"}]
        },
    }


def _pypistats_json(last_month: int = 500) -> dict:
    return {"data": {"last_month": last_month, "last_week": 100, "last_day": 15}}


def _make_response(status_code: int = 200, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    return resp


def _make_http_client(responses: list) -> MagicMock:
    """Build a mock httpx.Client context manager that returns responses in order."""
    client = MagicMock()
    client.get.side_effect = responses
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=client)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFetchHappyPath:
    def test_returns_items_for_two_packages(self):
        """Happy path: user has 2 packages, both succeed."""
        user_packages = [("Owner", "alpha"), ("Owner", "beta")]
        responses = [
            _make_response(200, _pypi_json("alpha", "1.0.0", "alice")),
            _make_response(200, _pypistats_json(1000)),
            _make_response(200, _pypi_json("beta", "2.3.1", "alice")),
            _make_response(200, _pypistats_json(250)),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert len(items) == 2
        assert items[0].title == "alpha"
        assert items[0].score == 1000
        assert items[1].title == "beta"
        assert items[1].score == 250

    def test_item_url_format(self):
        """URL should point to the correct PyPI project page."""
        user_packages = [("Owner", "mypackage")]
        responses = [
            _make_response(200, _pypi_json("mypackage")),
            _make_response(200, _pypistats_json()),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert items[0].url == "https://pypi.org/project/mypackage/"

    def test_item_body_contains_version_and_downloads(self):
        """Body string should include the version and download count."""
        user_packages = [("Owner", "mypackage")]
        responses = [
            _make_response(200, _pypi_json("mypackage", "3.1.4")),
            _make_response(200, _pypistats_json(9999)),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert "v3.1.4" in items[0].body
        assert "9,999" in items[0].body  # formatted with commas

    def test_item_body_contains_days_ago(self):
        """Body string should include a 'd ago' suffix for the release age."""
        user_packages = [("Owner", "mypackage")]
        responses = [
            _make_response(200, _pypi_json("mypackage")),
            _make_response(200, _pypistats_json()),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert "d ago" in items[0].body

    def test_item_created_at_is_timezone_aware_datetime(self):
        """created_at must be a UTC-aware datetime."""
        user_packages = [("Owner", "mypackage")]
        responses = [
            _make_response(200, _pypi_json("mypackage")),
            _make_response(200, _pypistats_json()),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert isinstance(items[0].created_at, datetime)
        assert items[0].created_at.tzinfo is not None


class TestFetchEdgeCases:
    def test_empty_user(self):
        """User with no packages returns empty list."""
        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls:
            mock_proxy_cls.return_value.user_packages.return_value = []
            items = fetch("nobody")

        assert items == []

    def test_username_none_raises_value_error(self):
        """fetch(None) raises ValueError."""
        with pytest.raises(ValueError, match="username is required"):
            fetch(None)

    def test_username_empty_string_raises_value_error(self):
        """fetch('') raises ValueError."""
        with pytest.raises(ValueError, match="username is required"):
            fetch("")

    def test_skips_package_with_404(self):
        """If a package's PyPI JSON returns 404, it is skipped gracefully."""
        user_packages = [("Owner", "good"), ("Owner", "bad")]
        responses = [
            _make_response(200, _pypi_json("good")),
            _make_response(200, _pypistats_json()),
            _make_response(404),  # bad package fails
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert len(items) == 1
        assert items[0].title == "good"

    def test_pypistats_failure_gives_zero_downloads(self):
        """If pypistats returns 500, downloads = 0, package is still included."""
        user_packages = [("Owner", "mypkg")]
        responses = [
            _make_response(200, _pypi_json("mypkg")),
            _make_response(500),  # pypistats fails
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice")

        assert len(items) == 1
        assert items[0].score == 0

    def test_respects_limit(self):
        """With 5 packages and limit=2, only 2 items are returned."""
        user_packages = [("Owner", f"pkg{i}") for i in range(5)]
        responses = [
            _make_response(200, _pypi_json("pkg0")),
            _make_response(200, _pypistats_json()),
            _make_response(200, _pypi_json("pkg1")),
            _make_response(200, _pypistats_json()),
        ]

        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls, \
             patch("httpx.Client", return_value=_make_http_client(responses)):
            mock_proxy_cls.return_value.user_packages.return_value = user_packages
            items = fetch("alice", limit=2)

        assert len(items) == 2

    def test_fetch_calls_pypi_xmlrpc_endpoint(self):
        """fetch() connects to the official PyPI XML-RPC endpoint."""
        with patch("xmlrpc.client.ServerProxy") as mock_proxy_cls:
            mock_proxy_cls.return_value.user_packages.return_value = []
            fetch("alice")
        mock_proxy_cls.assert_called_once_with("https://pypi.org/pypi")
