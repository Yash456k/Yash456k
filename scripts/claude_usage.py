#!/usr/bin/env python3
"""Count daily AI coding tokens (Claude Code and Codex) and draw the activity graph.

Claude Code writes every session to ~/.claude/projects/**/*.jsonl, and each reply
there carries its token usage. This script adds those up per day across the WSL
and Windows installs. Codex daily totals come from the public activity API behind
yash456k.com, which the Hermes server refreshes nightly.

Both go into data/usage.json, which the interactive page (index.html) reads, and
the README graph is redrawn as assets/activity-{light,dark}.svg. Claude Code
deletes transcripts after 30 days and the API only covers the last year, so the
history file is the record: each day keeps its largest count ever seen.

Run with --push to commit and push when anything changed.
"""

from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
HISTORY_PATH = REPO / "data" / "usage.json"
CARD_PATHS = {theme: REPO / "assets" / f"activity-{theme}.svg" for theme in ("light", "dark")}
FONT_DIR = REPO / "assets" / "fonts"
TRANSCRIPT_ROOTS = [os.path.expanduser("~/.claude/projects"), *glob.glob("/mnt/c/Users/*/.claude/projects")]
CODEX_URL = "https://api.yash456k.com/v1/activity"
PAGE_URL = "https://yash456k.github.io/Yash456k/"
TZ = ZoneInfo("Asia/Kolkata")

# GitHub's own colors for text and lines, so the graph sits in the README like its
# contribution graph does, with the warm ramp of the activity card on yash456k.com.
THEMES = {
    "light": {"ink": "#1f2328", "muted": "#59636e", "edge": "#d1d9e0", "link": "#0969da",
              "empty": "#eff2f5", "levels": ["#fcd9c5", "#f4a47f", "#de6d47", "#a8452a"]},
    "dark": {"ink": "#f0f6fc", "muted": "#9198a1", "edge": "#3d444d", "link": "#4493f8",
             "empty": "#151b23", "levels": ["#4a2a1f", "#8a4430", "#c8623f", "#f59a74"]},
}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def font_faces(*faces: tuple[str, str, int, str]) -> str:
    """Inline fonts as data URIs; GitHub shows SVGs as images, which can't load anything else."""
    css = []
    for family, file, weight, style in faces:
        data = base64.b64encode((FONT_DIR / file).read_bytes()).decode()
        css.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:{style};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
    return "".join(css)


def scan_claude() -> dict[str, dict[str, int]]:
    days: dict[str, dict[str, int]] = {}
    seen: set[tuple[str, str]] = set()
    for root in TRANSCRIPT_ROOTS:
        for path in glob.glob(f"{root}/**/*.jsonl", recursive=True):
            with open(path, encoding="utf-8", errors="ignore") as file:
                for line in file:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = entry.get("message")
                    usage = message.get("usage") if isinstance(message, dict) else None
                    if entry.get("type") != "assistant" or not usage or "timestamp" not in entry:
                        continue
                    # One reply is logged once per content block, all with the same usage.
                    key = (message.get("id"), entry.get("requestId"))
                    if key in seen:
                        continue
                    seen.add(key)
                    day = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).astimezone(TZ)
                    totals = days.setdefault(day.date().isoformat(), {"claude": 0, "claude_written": 0})
                    totals["claude_written"] += usage.get("output_tokens", 0)
                    totals["claude"] += (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )
    return days


def fetch_codex() -> dict[str, dict[str, int]]:
    """Codex days from the public API; on failure keep the history and say so."""
    try:
        request = Request(CODEX_URL, headers={"User-Agent": "Yash456k profile graph"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS URL
            days = json.load(response)["codex"]["days"]
        return {day["date"]: {"codex": int(day["tokens"])} for day in days}
    except Exception as error:  # noqa: BLE001 - a stale Codex count must not stop the Claude update
        print(f"Codex fetch failed, keeping saved days: {error}", file=sys.stderr)
        return {}


def merge(history: dict[str, dict[str, int]], *sources: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    merged = {day: dict(totals) for day, totals in history.items()}
    for source in sources:
        for day, totals in source.items():
            saved = merged.setdefault(day, {})
            for field, value in totals.items():
                saved[field] = max(saved.get(field, 0), value)
    return dict(sorted(merged.items()))


def total(totals: dict[str, int]) -> int:
    return totals.get("claude", 0) + totals.get("codex", 0)


def short(n: float) -> str:
    for size, suffix, digits in ((1e9, "B", 2), (1e6, "M", 1), (1e3, "K", 1)):
        if n >= size:
            return f"{n / size:.{digits}f}{suffix}"
    return str(int(n))


def render(days: dict[str, dict[str, int]], today: date, theme: str) -> str:
    """A contribution graph for the last 12 months, laid out like GitHub's."""
    colors = THEMES[theme]
    weeks, pitch, cell = 53, 15, 11
    calendar_end = today + timedelta(days=(5 - today.weekday()) % 7)  # through Saturday
    calendar_start = calendar_end - timedelta(days=weeks * 7 - 1)
    year = {day: t for day, t in days.items() if calendar_start.isoformat() <= day <= today.isoformat() and total(t)}
    claude = sum(t.get("claude", 0) for t in year.values())
    codex = sum(t.get("codex", 0) for t in year.values())

    # Same banding as the site: ordinary days stay quiet, the top 5% light up.
    counts = sorted(total(t) for t in year.values())
    thresholds = [counts[int((len(counts) - 1) * f)] for f in (0.5, 0.75, 0.95)]

    width, height = 860, 224
    box_y, left, grid_y = 34, 48, 34 + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t">',
        f'<title id="t">{short(claude + codex)} AI coding tokens in the last year: '
        f'Claude Code {short(claude)}, Codex {short(codex)}</title>',
        f"<style>text{{font-family:{FONT}}}</style>",
        f'<text x="1" y="20" fill="{colors["ink"]}" font-size="16">'
        f'<tspan font-weight="600">{short(claude + codex)}</tspan> tokens with AI coding agents in the last year</text>',
        f'<text x="{width - 1}" y="20" fill="{colors["muted"]}" font-size="13" text-anchor="end">'
        f'Claude Code <tspan fill="{colors["ink"]}" font-weight="600">{short(claude)}</tspan>'
        f'<tspan dx="10">·</tspan><tspan dx="10">Codex </tspan>'
        f'<tspan fill="{colors["ink"]}" font-weight="600">{short(codex)}</tspan></text>',
        f'<rect x="0.5" y="{box_y + 0.5}" width="{width - 1}" height="{height - box_y - 1}" rx="6" '
        f'fill="none" stroke="{colors["edge"]}"/>',
    ]

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="16" y="{grid_y + row * pitch + 9.5}" fill="{colors["ink"]}" font-size="12">{name}</text>')

    markers: list[tuple[int, str]] = []
    for week in range(weeks):
        middle = calendar_start + timedelta(days=week * 7 + 3)
        if not markers or markers[-1][1] != f"{middle:%b}":
            markers.append((week, f"{middle:%b}"))
    for index, (week, label) in enumerate(markers):
        if index + 1 < len(markers) and markers[index + 1][0] - week < 3:
            continue  # a short leading month would collide with the next label
        out.append(f'<text x="{left + week * pitch}" y="{grid_y - 9}" fill="{colors["ink"]}" font-size="12">{label}</text>')

    for offset in range(weeks * 7):
        day = calendar_start + timedelta(days=offset)
        if day > today:
            break
        tokens = total(year.get(day.isoformat(), {}))
        level = 0 if tokens == 0 else 1 + sum(tokens > t for t in thresholds)
        fill = colors["empty"] if level == 0 else colors["levels"][level - 1]
        out.append(
            f'<rect x="{left + (offset // 7) * pitch}" y="{grid_y + (offset % 7) * pitch}" '
            f'width="{cell}" height="{cell}" rx="2" fill="{fill}"/>'
        )

    footer_y = grid_y + 7 * pitch + 30
    out.append(
        f'<text x="16" y="{footer_y}" fill="{colors["link"]}" font-size="12">'
        f'Explore day by day at yash456k.github.io/Yash456k ↗</text>'
    )
    legend_x = width - 16 - 30 - 5 * pitch - 6
    out.append(f'<text x="{legend_x - 6}" y="{footer_y}" fill="{colors["muted"]}" font-size="12" text-anchor="end">Less</text>')
    for level in range(5):
        fill = colors["empty"] if level == 0 else colors["levels"][level - 1]
        out.append(f'<rect x="{legend_x + level * pitch}" y="{footer_y - 10}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')
    out += [
        f'<text x="{legend_x + 5 * pitch + 2}" y="{footer_y}" fill="{colors["muted"]}" font-size="12">More</text>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="commit and push when anything changed")
    args = parser.parse_args()

    if args.push:
        git("pull", "--rebase", "--autostash", "-q")
    history = json.loads(HISTORY_PATH.read_text()) if HISTORY_PATH.exists() else {}
    days = merge(history, scan_claude(), fetch_codex())
    HISTORY_PATH.parent.mkdir(exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(days, indent=1) + "\n")
    today = datetime.now(TZ).date()
    for theme, path in CARD_PATHS.items():
        path.write_text(render(days, today, theme))

    claude = sum(t.get("claude", 0) for t in days.values())
    codex = sum(t.get("codex", 0) for t in days.values())
    print(f"{len(days)} days: Claude Code {claude:,}, Codex {codex:,} tokens")
    if args.push and git("status", "--porcelain", "data", "assets").strip():
        git("add", "data", "assets")
        git("commit", "-q", "-m", "Update AI activity")
        git("push", "-q", "origin", "HEAD:main")
        print("pushed")


if __name__ == "__main__":
    main()
