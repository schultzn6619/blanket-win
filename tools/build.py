#!/usr/bin/env python3
# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Build the data files Blanket needs at runtime

Compiles the Blueprint UI files and bundles them with the icons and sounds
into a GResource, compiles the GSettings schema and the translations.
Everything lands in build/data, where Blanket looks for it when run from a
checkout (python -m blanket) and which the Windows bundle ships as is.

Usage:
    python tools/build.py           build the data files
    python tools/build.py --clean   remove the build directory first
    python tools/build.py pot       regenerate po/blanket.pot

Needs blueprint-compiler, glib-compile-resources, glib-compile-schemas,
xmllint and msgfmt (and xgettext for "pot") on the PATH.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
UI_DIR = BUILD / "ui"
DATA_DIR = BUILD / "data"

RESOURCES = ROOT / "data" / "resources"
SCHEMA = ROOT / "data" / "com.rafaelmardojai.Blanket.gschema.xml"
ICON = ROOT / "data" / "blanket.ico"
PO_DIR = ROOT / "po"
GETTEXT_PACKAGE = "blanket"


class BuildError(Exception):
    pass


def find_tool(name: str) -> list[str]:
    """
    Command prefix to run a build tool

    On Windows a few of them (blueprint-compiler) are Python scripts without
    an extension, which cannot be executed directly.
    """
    path = shutil.which(name)
    if path is None:
        raise BuildError(f"{name} was not found on the PATH")

    if sys.platform == "win32" and Path(path).suffix.lower() not in (
        ".exe",
        ".bat",
        ".cmd",
    ):
        with open(path, "rb") as script:
            if b"python" in script.readline():
                return [sys.executable, path]

    return [path]


def run(command: list[str | Path]):
    printable = " ".join(str(arg) for arg in command)
    print(f"  $ {printable}")
    result = subprocess.run([str(arg) for arg in command], cwd=ROOT)
    if result.returncode != 0:
        raise BuildError(f"command failed with exit code {result.returncode}")


def compile_blueprints():
    print("Compiling Blueprint UI files")
    blueprints = sorted(RESOURCES.glob("*.blp"))
    UI_DIR.mkdir(parents=True, exist_ok=True)
    run(
        find_tool("blueprint-compiler")
        + ["batch-compile", UI_DIR, RESOURCES]
        + blueprints
    )


def compile_resources():
    print("Compiling GResource bundle")
    # glib-compile-resources needs xmllint for the xml-stripblanks preprocessing
    find_tool("xmllint")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run(
        find_tool("glib-compile-resources")
        + [
            f"--sourcedir={UI_DIR}",
            f"--sourcedir={RESOURCES}",
            f"--sourcedir={ROOT / 'data'}",  # App icon
            f"--target={DATA_DIR / 'blanket.gresource'}",
            RESOURCES / "blanket.gresource.xml",
        ]
    )


def copy_icon():
    print("Copying Windows icon")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ICON, DATA_DIR / ICON.name)


def compile_schemas():
    print("Compiling GSettings schema")
    schemas = DATA_DIR / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCHEMA, schemas / SCHEMA.name)
    run(find_tool("glib-compile-schemas") + ["--strict", schemas])


def compile_translations():
    print("Compiling translations")
    msgfmt = find_tool("msgfmt")
    languages = (PO_DIR / "LINGUAS").read_text(encoding="utf-8").split()

    for lang in languages:
        out_dir = DATA_DIR / "locale" / lang / "LC_MESSAGES"
        out_dir.mkdir(parents=True, exist_ok=True)
        run(
            msgfmt
            + [
                "--check-format",
                "-o",
                out_dir / f"{GETTEXT_PACKAGE}.mo",
                PO_DIR / f"{lang}.po",
            ]
        )


def update_pot():
    print("Updating translation template")
    sources = [
        line.strip()
        for line in (PO_DIR / "POTFILES").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    pot = PO_DIR / f"{GETTEXT_PACKAGE}.pot"
    keywords = ["--keyword=_", "--keyword=N_", "--keyword=C_:1c,2", "--keyword=NC_:1c,2"]
    common = [
        "--from-code=UTF-8",
        "--add-comments",
        f"--package-name={GETTEXT_PACKAGE}",
        "-o",
        pot,
    ] + keywords

    # Blueprint is close enough to C for xgettext to find the strings
    by_language = {
        "Python": [s for s in sources if s.endswith(".py")],
        "C": [s for s in sources if s.endswith(".blp")],
        "GSettings": [s for s in sources if s.endswith(".gschema.xml")],
    }

    first = True
    for language, files in by_language.items():
        if not files:
            continue
        run(
            find_tool("xgettext")
            + common
            + [f"--language={language}"]
            + ([] if first else ["--join-existing"])
            + files
        )
        first = False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("target", nargs="?", choices=["data", "pot"], default="data")
    parser.add_argument("--clean", action="store_true", help="start from scratch")
    args = parser.parse_args()

    try:
        if args.target == "pot":
            update_pot()
            return 0

        if args.clean and BUILD.exists():
            shutil.rmtree(BUILD)

        compile_blueprints()
        compile_resources()
        copy_icon()
        compile_schemas()
        compile_translations()
    except BuildError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Done, data files are in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
