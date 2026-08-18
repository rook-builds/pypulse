"""pypulse core — the one file you actually need to write.

The Item model and all four formatters below are DONE and tested. The only
function left to implement is `fetch()`: make the real request to PyPI package portfolio stats,
turn each result into an `Item`, and return the list. Delete the
NotImplementedError once it works.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional

import httpx


@dataclass
class Item:
    """One thing from PyPI package portfolio stats — a story, post, repo event, feed entry…"""

    title: str
    url: str
    author: str = ""
    score: int = 0
    comments: int = 0
    created_at: Optional[datetime] = None
    body: str = ""

    def _created_iso(self) -> str:
        return self.created_at.isoformat() if self.created_at else ""


# --------------------------------------------------------------------------- #
# fetch — THE PART YOU WRITE. Everything below fetch is already finished.
# --------------------------------------------------------------------------- #
def fetch(username: Optional[str] = None, limit: int = 10) -> list[Item]:
    """Fetch up to `limit` items from PyPI package portfolio stats and return them as Items.

    Replace the body below with a real request. `httpx` is already a dependency:

        with httpx.Client(timeout=15, headers={"User-Agent": "pypulse"}) as c:
            data = c.get("https://...").json()
        return [Item(title=..., url=..., score=...) for row in data[:limit]]
    """
    raise NotImplementedError(
        "pypulse.fetch() is a scaffold stub — implement the real PyPI package portfolio stats request."
    )


# --------------------------------------------------------------------------- #
# formatters — DONE. Tested by tests/test_formatter.py. Do not rewrite.
# --------------------------------------------------------------------------- #
def to_text(items: list[Item], source: str = "pypulse") -> str:
    if not items:
        return f"# {source}\n\nNo items found."
    lines = [f"# {source}", ""]
    for i, it in enumerate(items, 1):
        meta = []
        if it.score:
            meta.append(f"{it.score} points")
        if it.comments:
            meta.append(f"{it.comments} comments")
        if it.author:
            meta.append(f"by {it.author}")
        suffix = f"  ({' · '.join(meta)})" if meta else ""
        lines.append(f"{i}. **{it.title}**{suffix}")
        if it.url:
            lines.append(f"   {it.url}")
        if it.body:
            lines.append(f"   {it.body}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_json(items: list[Item], source: str = "pypulse") -> str:
    payload = {
        "source": source,
        "count": len(items),
        "items": [
            {**asdict(it), "created_at": it._created_iso()} for it in items
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def to_table(items: list[Item], source: str = "pypulse") -> str:
    if not items:
        return "No items found."
    header = "| # | Title | Score | Comments | Author |"
    sep = "|---|-------|-------|----------|--------|"
    rows = [header, sep]
    for i, it in enumerate(items, 1):
        title = it.title.replace("|", "\\|")
        rows.append(
            f"| {i} | {title} | {it.score} | {it.comments} | {it.author} |"
        )
    return "\n".join(rows)


def to_csv(items: list[Item], source: str = "pypulse") -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["title", "url", "author", "score", "comments", "created_at"])
    for it in items:
        w.writerow(
            [it.title, it.url, it.author, it.score, it.comments, it._created_iso()]
        )
    return buf.getvalue()
