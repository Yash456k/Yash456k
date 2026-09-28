#!/usr/bin/env python3
"""Draw the profile hero, the headline from yash456k.com, in light and dark versions."""

from __future__ import annotations

from claude_usage import REPO, font_faces

THEMES = {
    "light": {"ink": "#191714", "muted": "#716b66", "accent": "#b83d32", "disc": "#b83d32", "disc_opacity": 0.07, "ring": "#b83d32", "ring_opacity": 0.14},
    "dark": {"ink": "#f5efe6", "muted": "#a39b93", "accent": "#ec7a64", "disc": "#ec7a64", "disc_opacity": 0.07, "ring": "#ffffff", "ring_opacity": 0.09},
}


def render(theme: dict[str, str | float]) -> str:
    rings = "".join(
        f'<circle cx="772" cy="92" r="{r}" fill="none" stroke="{theme["ring"]}" stroke-opacity="{theme["ring_opacity"]}"/>'
        for r in (196, 272)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320" role="img" aria-labelledby="t">
<title id="t">Yash Khambhatta. I build stuff I find interesting. Full-stack engineer at AIVID Techvision, Ahmedabad, India.</title>
<style>{font_faces(
    ("Newsreader", "newsreader.woff2", 400, "normal"),
    ("Newsreader", "newsreader-italic.woff2", 400, "italic"),
    ("DM Sans", "dmsans-400.woff2", 400, "normal"),
)}
.serif{{font-family:Newsreader,Georgia,serif}}.sans{{font-family:'DM Sans',-apple-system,'Segoe UI',sans-serif}}
.orbit{{transform-origin:772px 92px;animation:orbit 48s linear infinite}}@keyframes orbit{{to{{transform:rotate(360deg)}}}}
@media (prefers-reduced-motion:reduce){{.orbit{{animation:none}}}}</style>
<circle cx="772" cy="92" r="128" fill="{theme["disc"]}" fill-opacity="{theme["disc_opacity"]}"/>{rings}
<g class="orbit"><circle cx="{772 - 196 * 0.94:.1f}" cy="{92 + 196 * 0.34:.1f}" r="3.5" fill="{theme["accent"]}"/></g>
<text class="serif" x="6" y="40" font-size="24" fill="{theme["ink"]}">Yash Khambhatta</text>
<text class="serif" x="4" y="152" font-size="96" letter-spacing="-4.8" fill="{theme["ink"]}">I build stuff</text>
<text class="serif" x="8" y="238" font-size="88" font-style="italic" letter-spacing="-3.96" fill="{theme["accent"]}" style="font-variant-ligatures:none">I find interesting.</text>
<text class="sans" x="8" y="294" font-size="19" fill="{theme["muted"]}">Full-stack engineer at AIVID Techvision  ·  Ahmedabad, India</text>
</svg>
"""


if __name__ == "__main__":
    for name, theme in THEMES.items():
        (REPO / "assets" / f"hero-{name}.svg").write_text(render(theme))
