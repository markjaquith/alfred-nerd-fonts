#!/usr/bin/env python3
# Copyright (c) 2026 Mark Jaquith
# SPDX-License-Identifier: MIT
"""Alfred Script Filter for searching Nerd Fonts symbols."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent / "data" / "nerd-font-glyphs.json"
FONT_PATH = Path(__file__).resolve().parent / "data" / "fonts" / "SymbolsNerdFontMono-Regular.ttf"
ICON_DIR = Path(__file__).resolve().parent / "icons"
RENDERER_SOURCE = Path(__file__).resolve().parent / "render-icon.swift"
RENDERER_PATH = Path(__file__).resolve().parent / "bin" / "render-icon"
MAX_RESULTS = 80

COLLECTION_NAMES = {
    "cod": "Codicons",
    "custom": "Nerd Fonts custom",
    "dev": "Devicons",
    "fa": "Font Awesome",
    "fae": "Font Awesome Extension",
    "iec": "IEC Power Symbols",
    "indent": "Indentation",
    "linux": "Linux",
    "md": "Material Design",
    "oct": "Octicons",
    "pl": "Powerline",
    "ple": "Powerline Extra",
    "pom": "Pomicons",
    "seti": "Seti UI",
    "weather": "Weather Icons",
}


def alfred(items: list[dict[str, Any]]) -> None:
    print(json.dumps({"items": items}, ensure_ascii=False))


def normalize_query(query: str) -> list[str]:
    query = query.strip().lower()

    if len(query) == 1 and ord(query) > 255:
        return [f"{ord(query):x}"]

    query = re.sub(r"^u\+", "", query)
    return [term for term in re.split(r"[\s_-]+", query) if term]


def score_glyph(glyph: dict[str, Any], query: str, terms: list[str]) -> float | None:
    name = str(glyph["name"]).lower()
    short_name = re.sub(r"^(?:nf|nfold)-", "", name)
    symbol_name = name.split("-", 2)[2] if name.count("-") >= 2 else short_name
    codepoint = str(glyph["codepoint"]).lower()
    character = str(glyph["character"])
    tokens = list(glyph.get("tokens", []))

    if not terms:
        return None

    if query == character or query == codepoint or query == f"u+{codepoint}":
        return 0

    score = 0.0
    for term in terms:
        if term == codepoint or term == f"u+{codepoint}":
            term_score = 0.0
        elif term == name or term == short_name:
            term_score = 1.0
        elif term in tokens:
            term_score = 5.0
        elif any(token.startswith(term) for token in tokens):
            term_score = 15.0
        elif term in name:
            term_score = 40.0 + (name.index(term) / 100.0)
        else:
            return None

        score += term_score

    if symbol_name == query:
        score -= 20.0
    elif symbol_name.startswith(query):
        score -= 8.0

    if short_name == query or name == query:
        score -= 10.0
    elif short_name.startswith(query) or name.startswith(query):
        score -= 5.0

    if glyph.get("removed"):
        score += 1000.0

    return score


def subtitle_for(glyph: dict[str, Any]) -> str:
    codepoint = str(glyph["codepoint"]).upper()
    collection = str(glyph.get("collection") or "unknown")
    collection_name = COLLECTION_NAMES.get(collection, collection)
    status = "removed upstream" if glyph.get("removed") else "Enter to paste symbol"
    return f"U+{codepoint} - {collection_name} - {status}"


def icon_path_for(glyph: dict[str, Any]) -> Path:
    return ICON_DIR / f"{glyph['name']}.png"


def ensure_renderer(force_compile: bool = False) -> Path | None:
    if not FONT_PATH.exists() or not RENDERER_SOURCE.exists():
        return None

    needs_compile = force_compile or not RENDERER_PATH.exists()
    if not needs_compile:
        needs_compile = RENDERER_PATH.stat().st_mtime < RENDERER_SOURCE.stat().st_mtime

    if needs_compile:
        RENDERER_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["/usr/bin/swiftc", "-O", str(RENDERER_SOURCE), "-o", str(RENDERER_PATH)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    return RENDERER_PATH if RENDERER_PATH.exists() else None


def ensure_icons(glyphs: list[dict[str, Any]]) -> None:
    missing = [(str(glyph["character"]), icon_path_for(glyph)) for glyph in glyphs if not icon_path_for(glyph).exists()]
    if not missing:
        return

    renderer = ensure_renderer()
    if renderer is None:
        return

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    def render_with(renderer_path: Path) -> bool:
        args = [str(renderer_path), str(FONT_PATH), "96", "#5ac8fa"]
        for character, path in missing:
            args.extend([character, str(path)])

        try:
            subprocess.run(
                args,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    if render_with(renderer):
        return

    renderer = ensure_renderer(force_compile=True)
    if renderer is not None:
        render_with(renderer)


def item_for(glyph: dict[str, Any]) -> dict[str, Any]:
    name = str(glyph["name"])
    character = str(glyph["character"])
    codepoint = str(glyph["codepoint"]).upper()

    item: dict[str, Any] = {
        "uid": name,
        "title": name,
        "subtitle": subtitle_for(glyph),
        "arg": character,
        "autocomplete": name,
        "text": {
            "copy": character,
            "largetype": f"{character}  {name}  U+{codepoint}",
        },
        "mods": {
            "cmd": {
                "arg": name,
                "subtitle": f"Paste class name: {name}",
            },
            "alt": {
                "arg": f"U+{codepoint}",
                "subtitle": f"Paste codepoint: U+{codepoint}",
            },
        },
    }

    icon_path = icon_path_for(glyph)
    if icon_path.exists():
        item["icon"] = {"path": str(icon_path)}

    return item


def main() -> None:
    query = " ".join(sys.argv[1:]).strip().lower()

    if not DATA_PATH.exists():
        alfred(
            [
                {
                    "title": "Nerd Fonts index is missing",
                    "subtitle": "Run: /usr/bin/python3 update-icons.py",
                    "valid": False,
                }
            ]
        )
        return

    if not query:
        alfred(
            [
                {
                    "title": "Search Nerd Font symbols",
                    "subtitle": "Try: leaf, github, python, folder, md leaf, fa user, or U+F032A",
                    "valid": False,
                }
            ]
        )
        return

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    terms = normalize_query(query)
    matches: list[tuple[float, dict[str, Any]]] = []

    for glyph in data["glyphs"]:
        score = score_glyph(glyph, query, terms)
        if score is not None:
            matches.append((score, glyph))

    matches.sort(key=lambda result: (result[0], result[1]["name"]))

    if not matches:
        alfred(
            [
                {
                    "title": "No Nerd Font symbols found",
                    "subtitle": f"No matches for: {query}",
                    "valid": False,
                }
            ]
        )
        return

    glyphs = [glyph for _, glyph in matches[:MAX_RESULTS]]
    ensure_icons(glyphs)
    alfred([item_for(glyph) for glyph in glyphs])


if __name__ == "__main__":
    main()
