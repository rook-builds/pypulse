"""pypulse core — PyPI package portfolio health dashboard."""
from __future__ import annotations

import csv
import io
import json
import xmlrpc.client
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional

import httpx


@dataclass
class Item:
    """One PyPI package — name, version, downloads, release age."""

    title: str
    url: str
    author: str = ""
    score: int = 0          # downloads last 30 days
    comments: int = 0       # days since last release
    created_at: Optional[datetime] = None
    body: str = ""

    def _created_iso(self) -> str:
        return self.created_at.isoformat() if self.created_at else ""


# --------------------------------------------------------------------------- #
# fetch — PyPI package portfolio stats
# --------------------------------------------------------------------------- #
def fetch(username: Optional[str] = None, limit: int = 10) -> list[Item]:
    """Fetch PyPI package health stats for a given PyPI username.

    For each package owned by the user, returns an Item with:
      - title: package name
      - url: PyPI project page
      - author: declared package author
      - score: downloads in the last 30 days (from pypistats.org)
      - body: "vX.Y.Z · N dl/mo · Nd ago" summary line
      - created_at: release date of latest version (UTC-aware datetime)
    """
    if not username:
        raise ValueError("username is required — pass a PyPI username")

    # Step 1: list packages via PyPI XML-RPC
    proxy = xmlrpc.client.ServerProxy("https://pypi.org/pypi")
    try:
        raw = proxy.user_packages(username)  # [(role, package_name), ...]
    except Exception as exc:
        raise RuntimeError(f"Could not fetch packages for '{username}': {exc}") from exc

    package_names = [name for _role, name in raw]
    if not package_names:
        return []

    package_names = package_names[:limit]
    items = []
    now = datetime.now(timezone.utc)

    with httpx.Client(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "pypulse/0.1.0"},
    ) as c:
        for pkg_name in package_names:
            try:
                # Step 2: package metadata
                meta_resp = c.get(f"https://pypi.org/pypi/{pkg_name}/json")
                if meta_resp.status_code != 200:
                    continue
                data = meta_resp.json()
                info = data["info"]
                version = info["version"]

                # Parse release date for latest version
                release_date: Optional[datetime] = None
                releases = data.get("releases", {}).get(version, [])
                if releases:
                    ts = releases[0].get("upload_time_iso_8601", "")
                    if ts:
                        # Python 3.10 compat: replace "Z" before fromisoformat
                        release_date = datetime.fromisoformat(ts.replace("Z", "+00:00"))

                days_since_str = ""
                if release_date:
                    days_since = (now - release_date).days
                    days_since_str = f"{days_since}d ago"

                # Step 3: download stats from pypistats (graceful degradation)
                downloads = 0
                try:
                    dl_resp = c.get(
                        f"https://pypistats.org/api/packages/{pkg_name.lower()}/recent"
                    )
                    if dl_resp.status_code == 200:
                        downloads = dl_resp.json().get("data", {}).get("last_month", 0)
                except Exception:
                    pass

                body_parts = [f"v{version}", f"{downloads:,} dl/mo"]
                if days_since_str:
                    body_parts.append(days_since_str)

                items.append(
                    Item(
                        title=pkg_name,
                        url=f"https://pypi.org/project/{pkg_name}/",
                        author=info.get("author", ""),
                        score=downloads,
                        body=" · ".join(body_parts),
                        created_at=release_date,
                    )
                )
            except Exception:
                continue

    return items


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
            meta.append(f"{it.score} downloads/mo")
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
    header = "| # | Package | Downloads/mo | Released | Author |"
    sep = "|---|---------|-------------|----------|--------|"
    rows = [header, sep]
    for i, it in enumerate(items, 1):
        title = it.title.replace("|", "\\|")
        released = it.created_at.date().isoformat() if it.created_at else "—"
        rows.append(
            f"| {i} | {title} | {it.score:,} | {released} | {it.author} |"
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
