# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Blanket entry point, used by ``python -m blanket`` and the Windows executable
"""

import os
import signal
import sys


def run() -> int:
    from blanket import paths
    from blanket.system import IS_WINDOWS

    if IS_WINDOWS and not _windows_startup():
        return 0  # Handed over to the instance already running

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

    from blanket.system.i18n import setup_translations

    setup_translations(str(paths.locale_dir()))

    from gi.repository import Gio

    resource = Gio.Resource.load(str(paths.resource_file()))
    resource._register()  # type: ignore

    # Imported late, the sound titles are translated as the module loads
    from blanket import main

    return main.main()


def _windows_startup() -> bool:
    """
    Windows specific setup, False when Blanket should not start after all
    """
    from blanket.define import APP_ID
    from blanket.system import windows
    from blanket.system.windows import instance, win32

    windows.redirect_output_to_log()

    if not instance.acquire():
        # Autostart while already running has nothing to show
        if "--hidden" not in sys.argv and "-h" not in sys.argv:
            instance.activate_running_instance()
        return False

    win32.set_app_user_model_id(APP_ID)
    return True


if __name__ == "__main__":
    sys.exit(run())
