#!/usr/bin/env python3
"""Draw the profile hero, the headline from yash456k.com, in light and dark versions."""

from __future__ import annotations

from claude_usage import REPO, font_faces

THEMES = {
    "light": {"ink": "#191714", "muted": "#716b66", "accent": "#b83d32"},
    "dark": {"ink": "#f5efe6", "muted": "#a39b93", "accent": "#ec7a64"},
}


def render(theme: dict[str, str]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300" role="img" aria-labelledby="t">
<title id="t">Yash Khambhatta. I build stuff I find interesting. Full-stack engineer at AIVID Techvision, Ahmedabad, India.</title>
<style>{font_faces(
    ("Newsreader", "newsreader.woff2", 400, "normal"),
    ("Newsreader", "newsreader-italic.woff2", 400, "italic"),
    ("DM Sans", "dmsans-400.woff2", 400, "normal"),
)}
.serif{{font-family:Newsreader,Georgia,serif}}.sans{{font-family:'DM Sans',-apple-system,'Segoe UI',sans-serif}}</style>
<g text-anchor="middle">
<text class="serif" x="450" y="36" font-size="24" fill="{theme["ink"]}">Yash Khambhatta</text>
<text class="serif" x="450" y="142" font-size="96" letter-spacing="-4.8" fill="{theme["ink"]}">I build stuff</text>
<text class="serif" x="450" y="226" font-size="88" font-style="italic" letter-spacing="-3.96" fill="{theme["accent"]}" style="font-variant-ligatures:none">I find interesting.</text>
<text class="sans" x="450" y="284" font-size="19" fill="{theme["muted"]}">Full-stack engineer at AIVID Techvision  ·  Ahmedabad, India</text>
</g>
</svg>
"""


if __name__ == "__main__":
    for name, theme in THEMES.items():
        (REPO / "assets" / f"hero-{name}.svg").write_text(render(theme))
