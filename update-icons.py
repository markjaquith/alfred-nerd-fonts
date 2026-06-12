#!/usr/bin/env python3
"""Build the local Nerd Fonts glyph index used by the Alfred workflow."""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SOURCE_URL = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/gh-pages/_includes/css/nerd-fonts-generated.css"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "nerd-font-glyphs.json"
FONT_URL = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf"
FONT_PATH = Path(__file__).resolve().parent / "data" / "fonts" / "SymbolsNerdFontMono-Regular.ttf"
FONT_LICENSE_URL = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/NerdFontsSymbolsOnly/LICENSE"
FONT_LICENSE_PATH = Path(__file__).resolve().parent / "data" / "fonts" / "LICENSE"

RULE_RE = re.compile(
    r"\.((?:nf|nfold)-[A-Za-z0-9_-]+):before\s*\{\s*content:\s*\"([^\"]+)\"",
    re.MULTILINE,
)
VERSION_RE = re.compile(r"Version:\s*([^\n*]+)")


def decode_css_content(value: str) -> str:
    """Decode a CSS content string such as '\\f032a' into real text."""

    out: list[str] = []
    i = 0

    while i < len(value):
        if value[i] != "\\":
            out.append(value[i])
            i += 1
            continue

        match = re.match(r"\\([0-9a-fA-F]{1,6})\s?", value[i:])
        if match:
            out.append(chr(int(match.group(1), 16)))
            i += len(match.group(0))
            continue

        if i + 1 < len(value):
            out.append(value[i + 1])
            i += 2
        else:
            i += 1

    return "".join(out)


def collection_for(name: str) -> str:
    if name.startswith("nfold-"):
        return "removed"

    parts = name.split("-", 2)
    return parts[1] if len(parts) > 1 else "unknown"


def build_index(css: str) -> dict[str, object]:
    seen: set[str] = set()
    glyphs: list[dict[str, object]] = []
    version_match = VERSION_RE.search(css)

    for match in RULE_RE.finditer(css):
        name = match.group(1)
        if name in seen:
            continue

        seen.add(name)
        character = decode_css_content(match.group(2))
        if not character:
            continue

        codepoints = [f"{ord(char):x}" for char in character]
        plain_name = re.sub(r"^(?:nf|nfold)-", "", name)
        tokens = [token for token in re.split(r"[-_]+", plain_name.lower()) if token]

        glyphs.append(
            {
                "name": name,
                "character": character,
                "codepoint": " ".join(codepoints),
                "collection": collection_for(name),
                "removed": name.startswith("nfold-"),
                "tokens": tokens,
            }
        )

    glyphs.sort(key=lambda glyph: glyph["name"])

    return {
        "source": SOURCE_URL,
        "nerd_fonts_version": version_match.group(1).strip() if version_match else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(glyphs),
        "glyphs": glyphs,
    }


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as response:
        css = response.read().decode("utf-8")

    index = build_index(css)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FONT_URL) as response:
        FONT_PATH.write_bytes(response.read())
    with urllib.request.urlopen(FONT_LICENSE_URL) as response:
        FONT_LICENSE_PATH.write_bytes(response.read())

    print(
        f"Wrote {index['count']} glyphs from Nerd Fonts {index['nerd_fonts_version']} to {OUTPUT_PATH}"
    )
    print(f"Wrote preview font to {FONT_PATH}")
    print(f"Wrote preview font license to {FONT_LICENSE_PATH}")


if __name__ == "__main__":
    main()
