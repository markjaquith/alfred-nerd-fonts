#!/usr/bin/env python3
# Copyright (c) 2026 Mark Jaquith
# SPDX-License-Identifier: MIT
"""Build a self-contained Alfred workflow package."""

from __future__ import annotations

import shutil
import stat
import subprocess
import zipfile
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOW_NAME = "Nerd.Fonts.alfredworkflow"
BUILD_DIR = ROOT / "build" / "workflow"
DIST_DIR = ROOT / "dist"
OUTPUT_PATH = DIST_DIR / WORKFLOW_NAME
ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)

PACKAGE_FILES = [
    "info.plist",
    "icon.png",
    "README.md",
    "LICENSE",
    "nerd-fonts-search.py",
    "render-icon.swift",
    "update-icons.py",
    "data/nerd-font-glyphs.json",
    "data/fonts/SymbolsNerdFontMono-Regular.ttf",
    "data/fonts/LICENSE",
]


def copy_package_files() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    BUILD_DIR.mkdir(parents=True)

    for relative_path in PACKAGE_FILES:
        source = ROOT / relative_path
        if not source.exists():
            raise SystemExit(f"Missing required file: {relative_path}")

        destination = BUILD_DIR / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def compile_renderer() -> None:
    swiftc = shutil.which("swiftc") or "/usr/bin/swiftc"
    if not Path(swiftc).exists():
        print("swiftc not found; workflow can still compile previews on first use if swiftc exists there")
        return

    output = BUILD_DIR / "bin" / "render-icon"
    output.parent.mkdir(parents=True, exist_ok=True)

    if compile_universal_renderer(swiftc, output):
        return

    subprocess.run(
        [swiftc, "-O", str(ROOT / "render-icon.swift"), "-o", str(output)],
        check=True,
    )
    output.chmod(output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def compile_universal_renderer(swiftc: str, output: Path) -> bool:
    lipo = shutil.which("lipo") or "/usr/bin/lipo"
    if not Path(lipo).exists():
        return False

    arm64_output = output.with_suffix(".arm64")
    x86_output = output.with_suffix(".x86_64")

    commands = [
        [swiftc, "-O", "-target", "arm64-apple-macosx11.0", str(ROOT / "render-icon.swift"), "-o", str(arm64_output)],
        [swiftc, "-O", "-target", "x86_64-apple-macosx11.0", str(ROOT / "render-icon.swift"), "-o", str(x86_output)],
        [lipo, "-create", str(arm64_output), str(x86_output), "-output", str(output)],
    ]

    try:
        for command in commands:
            subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        for temporary_output in (arm64_output, x86_output):
            temporary_output.unlink(missing_ok=True)
        print("Universal renderer build failed; falling back to native architecture")
        return False

    for temporary_output in (arm64_output, x86_output):
        temporary_output.unlink(missing_ok=True)

    output.chmod(output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return True


def add_file(archive: zipfile.ZipFile, path: Path) -> None:
    relative_path = path.relative_to(BUILD_DIR)
    file_stat = path.stat()
    mode = stat.S_IMODE(file_stat.st_mode)

    info = zipfile.ZipInfo(str(relative_path))
    info.date_time = ZIP_TIMESTAMP
    info.external_attr = (mode & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, path.read_bytes())


def zip_workflow() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    with zipfile.ZipFile(OUTPUT_PATH, "w") as archive:
        for path in sorted(BUILD_DIR.rglob("*")):
            if path.is_file():
                add_file(archive, path)


def main() -> None:
    copy_package_files()
    compile_renderer()
    zip_workflow()
    checksum = sha256(OUTPUT_PATH.read_bytes()).hexdigest()
    print(f"Wrote {OUTPUT_PATH}")
    print(f"SHA256 {checksum}")


if __name__ == "__main__":
    main()
