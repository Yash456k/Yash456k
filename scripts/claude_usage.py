#!/usr/bin/env python3
"""Count daily Claude Code tokens and draw the activity card on the profile README.

Claude Code writes every session to ~/.claude/projects/**/*.jsonl, and each reply
there carries its token usage. This script adds those up per day across the WSL
and Windows installs, merges them into data/claude-usage.json, and redraws
assets/claude-activity.svg. Claude Code deletes transcripts after 30 days, so the
history file is the record: a day keeps its largest count ever seen.

Run with --push to commit and push the card when it changes.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
HISTORY_PATH = REPO / "data" / "claude-usage.json"
CARD_PATH = REPO / "assets" / "claude-activity.svg"
TRANSCRIPT_ROOTS = [os.path.expanduser("~/.claude/projects"), *glob.glob("/mnt/c/Users/*/.claude/projects")]
TZ = ZoneInfo("Asia/Kolkata")

# Colors follow the activity card on yash456k.com, in a terracotta ramp for Claude.
BG, EDGE, INK, MUTED, EMPTY = "#292623", "#4b443d", "#fffaf0", "#c8beb3", "#322e2a"
LEVELS = ["#55372e", "#8f4c38", "#c0654a", "#f59a74"]
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"


def scan_transcripts() -> dict[str, dict[str, int]]:
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
                    totals = days.setdefault(day.date().isoformat(), {"tokens": 0, "written": 0})
                    totals["written"] += usage.get("output_tokens", 0)
                    totals["tokens"] += (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )
    return days


def merge(history: dict[str, dict[str, int]], scanned: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    merged = dict(history)
    for day, totals in scanned.items():
        if totals["tokens"] >= merged.get(day, {}).get("tokens", 0):
            merged[day] = totals
    return dict(sorted(merged.items()))


def short(n: float) -> str:
    for size, suffix, digits in ((1e9, "B", 2), (1e6, "M", 1), (1e3, "K", 1)):
        if n >= size:
            return f"{n / size:.{digits}f}{suffix}"
    return str(int(n))


def long_date(day: date) -> str:
    return f"{day:%b} {day.day}, {day.year}"


def render(days: dict[str, dict[str, int]], today: date) -> str:
    active = {day: totals for day, totals in days.items() if totals["tokens"] > 0}
    total = sum(t["tokens"] for t in active.values())
    written = sum(t["written"] for t in active.values())
    peak_day = max(active, key=lambda d: active[d]["tokens"])
    first_day = date.fromisoformat(min(active))

    # Same banding as the site: ordinary days stay quiet, the top 5% light up.
    counts = sorted(t["tokens"] for t in active.values())
    thresholds = [counts[int((len(counts) - 1) * f)] for f in (0.5, 0.75, 0.95)]

    width, pad, pitch, cell, weeks = 640, 25, 10.5, 8, 53
    grid_x, grid_y = pad + 30, 228
    calendar_end = today + timedelta(days=(5 - today.weekday()) % 7)  # through Saturday
    calendar_start = calendar_end - timedelta(days=weeks * 7 - 1)
    height = 372

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + 14}" '
        f'viewBox="0 0 {width} {height + 14}" font-family="{FONT}" role="img" aria-labelledby="t d">',
        '<title id="t">Claude Code activity</title>',
        f'<desc id="d">{short(total)} tokens since {long_date(first_day)}, a daily average of '
        f'{short(total / len(active))}, and a peak of {short(active[peak_day]["tokens"])} on '
        f'{long_date(date.fromisoformat(peak_day))}.</desc>',
        # The stacked edges under the card, as on the site.
        f'<rect x="8" y="14" width="{width - 16}" height="{height}" rx="20" fill="#645443"/>',
        f'<rect x="4" y="7" width="{width - 8}" height="{height}" rx="21" fill="#453b31"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="22" fill="{BG}" stroke="{EDGE}"/>',
        f'<rect x="{pad}" y="{pad}" width="32" height="32" rx="8" fill="#35302b" stroke="{EDGE}"/>',
    ]
    for i in range(8):
        inner, outer = (3.5, 10) if i % 2 == 0 else (3.5, 7.5)
        out.append(
            f'<line x1="41" y1="{41 - inner}" x2="41" y2="{41 - outer}" stroke="{LEVELS[3]}" '
            f'stroke-width="2.2" stroke-linecap="round" transform="rotate({i * 45} 41 41)"/>'
        )
    out += [
        f'<text x="67" y="39" fill="{INK}" font-size="14" font-weight="600">Claude Code activity</text>',
        f'<text x="67" y="54" fill="{MUTED}" font-size="10">Last 12 months</text>',
        f'<text x="{width - pad}" y="45" fill="{MUTED}" font-size="10" text-anchor="end">'
        f'<tspan fill="{LEVELS[3]}">●</tspan>  Updated daily</text>',
        f'<path d="M{pad} 77.5H{width - pad}M{pad} 172.5H{width - pad}" stroke="{EDGE}"/>',
    ]

    unit = (width - 2 * pad) / 3.2
    columns = [pad, pad + 1.2 * unit, pad + 2.2 * unit]
    stats = [
        ("TOTAL TOKENS", short(total), f"since {long_date(first_day)}", 40),
        ("DAILY AVG", short(total / len(active)), "per active day", 28),
        ("PEAK", short(active[peak_day]["tokens"]), long_date(date.fromisoformat(peak_day)), 28),
    ]
    for index, (label, value, note, size) in enumerate(stats):
        x = columns[index] + (0 if index == 0 else 16)
        if index:
            out.append(f'<path d="M{columns[index]:.1f} 77.5V172.5" stroke="{EDGE}"/>')
        out += [
            f'<text x="{x:.1f}" y="103" fill="{MUTED}" font-size="9.5" font-weight="600" letter-spacing="0.8">{label}</text>',
            f'<text x="{x:.1f}" y="{103 + size}" fill="{INK}" font-size="{size}" font-weight="500" letter-spacing="-0.5">{value}</text>',
            f'<text x="{x:.1f}" y="161" fill="{MUTED}" font-size="10">{note}</text>',
        ]

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{pad}" y="{grid_y + row * pitch + cell - 0.5}" fill="{MUTED}" font-size="9.5">{name}</text>')

    markers: list[tuple[int, str]] = []
    for week in range(weeks):
        middle = calendar_start + timedelta(days=week * 7 + 3)
        if not markers or markers[-1][1] != f"{middle:%b}":
            markers.append((week, f"{middle:%b}"))
    for index, (week, label) in enumerate(markers):
        if index + 1 < len(markers) and markers[index + 1][0] - week < 4:
            continue
        out.append(f'<text x="{grid_x + week * pitch:.1f}" y="218" fill="{MUTED}" font-size="9.5">{label}</text>')

    for offset in range(weeks * 7):
        day = calendar_start + timedelta(days=offset)
        if day > today:
            break
        tokens = active.get(day.isoformat(), {}).get("tokens", 0)
        level = 0 if tokens == 0 else 1 + sum(tokens > t for t in thresholds)
        fill = EMPTY if level == 0 else LEVELS[level - 1]
        x, y = grid_x + (offset // 7) * pitch, grid_y + (offset % 7) * pitch
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')

    out += [
        f'<path d="M{pad} 325.5H{width - pad}" stroke="{EDGE}"/>',
        f'<text x="{pad}" y="349" fill="{MUTED}" font-size="10">'
        f'<tspan fill="{INK}" font-weight="600">{len(active)}</tspan> active days  ·  '
        f'<tspan fill="{INK}" font-weight="600">{short(written)}</tspan> tokens written by Claude</text>',
        f'<text x="{width - pad}" y="349" fill="{MUTED}" font-size="10" text-anchor="end">Counted from Claude Code sessions</text>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="commit and push when the card changes")
    args = parser.parse_args()

    if args.push:
        git("pull", "--rebase", "--autostash", "-q")
    history = json.loads(HISTORY_PATH.read_text()) if HISTORY_PATH.exists() else {}
    days = merge(history, scan_transcripts())
    HISTORY_PATH.parent.mkdir(exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(days, indent=1) + "\n")
    CARD_PATH.write_text(render(days, datetime.now(TZ).date()))

    total = sum(t["tokens"] for t in days.values())
    print(f"{len(days)} active days, {total:,} tokens")
    if args.push and git("status", "--porcelain", "data", "assets").strip():
        git("add", "data", "assets")
        git("commit", "-q", "-m", "Update Claude activity card")
        git("push", "-q", "origin", "HEAD:main")
        print("pushed")


if __name__ == "__main__":
    main()
