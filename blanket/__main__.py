# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Blanket entry point, used by ``python -m blanket`` and the Windows executable
"""

import gettext
import locale
import os
import signal
import sys


def run() -> int:
    from blanket import paths

    if not paths.resource_file().exists():
        print(
            f"Error: {paths.resource_file()} is missing, "
            "build the data files first with: python tools/build.py"
        )
        return 1

    # Our schema has to be found next to the system ones (GTK needs its own)
    schema_dirs = [str(paths.schemas_dir())]
    if current := os.environ.get("GSETTINGS_SCHEMA_DIR"):
        schema_dirs.append(current)
    os.environ["GSETTINGS_SCHEMA_DIR"] = os.pathsep.join(schema_dirs)

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    setup_translations(str(paths.locale_dir()))

    from gi.repository import Gio

    resource = Gio.Resource.load(str(paths.resource_file()))
    resource._register()  # type: ignore

    # Imported late, the sound titles are translated as the module loads
    from blanket import main

    return main.main()


def setup_translations(localedir: str):
    from blanket.paths import GETTEXT_PACKAGE

    gettext.install(GETTEXT_PACKAGE, localedir)

    try:
        locale.bindtextdomain(GETTEXT_PACKAGE, localedir)
        locale.textdomain(GETTEXT_PACKAGE)
    except Exception:
        print("Cannot set locale.")
    try:
        gettext.bindtextdomain(GETTEXT_PACKAGE, localedir)
        gettext.textdomain(GETTEXT_PACKAGE)
    except Exception:
        print("Cannot load translations.")


if __name__ == "__main__":
    sys.exit(run())
