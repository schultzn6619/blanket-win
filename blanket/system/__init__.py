# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Operating system integration

Everything that works differently on Windows and Linux (autostart, keeping
the computer awake, power saving, translations) lives in this package, so
the rest of the app does not have to care which one it runs on.

Windows only pieces are in blanket.system.windows and may only be imported
when IS_WINDOWS is true, they load Win32 libraries as they import.
"""

import sys

IS_WINDOWS = sys.platform == "win32"
