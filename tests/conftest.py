"""Shared fixtures for pypulse tests."""

from datetime import datetime, timezone

import pytest

from pypulse.core import Item


@pytest.fixture
def sample_items():
    return [
        Item(
            title="A first item",
            url="https://example.com/1",
            author="alice",
            score=42,
            comments=5,
            created_at=datetime(2026, 7, 10, 17, 43, 30, tzinfo=timezone.utc),
            body="Some body text.",
        ),
        Item(
            title="A second item, with commas",
            url="https://example.com/2",
            author="bob",
            score=100,
            comments=20,
            created_at=datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def empty_items():
    return []
