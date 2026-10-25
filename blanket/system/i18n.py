# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Translation setup

Python strings go through the gettext module, while the UI templates and the
settings schema are translated by GTK and GLib through libintl. Both have to
be pointed at our catalogs.
"""

import gettext
import locale
import os

from blanket.paths import GETTEXT_PACKAGE
from blanket.system import IS_WINDOWS


def setup_translations(localedir: str):
    if IS_WINDOWS:
        _set_language_from_windows()

    gettext.bindtextdomain(GETTEXT_PACKAGE, localedir)
    gettext.textdomain(GETTEXT_PACKAGE)
    gettext.install(GETTEXT_PACKAGE, localedir)

    if IS_WINDOWS:
        _bind_libintl_windows(localedir)
        return

    try:
        locale.bindtextdomain(GETTEXT_PACKAGE, localedir)
        locale.textdomain(GETTEXT_PACKAGE)
    except Exception:
        print("Cannot set locale.")


def _set_language_from_windows():
    """
    Choose the translation from the Windows display language

    Windows does not set the variables gettext reads the language from, so
    both Python and libintl would always fall back to English.
    """
    if any(os.environ.get(var) for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES")):
        return  # Explicitly chosen by the user

    from blanket.system.windows import win32

    if language := win32.user_ui_language():
        os.environ["LANGUAGE"] = language


def _bind_libintl_windows(localedir: str):
    """
    Bind our domain in the libintl GTK uses

    Python on Windows has no locale.bindtextdomain, so it is called directly.
    GLib has to be loaded first, then the library is already in the process.
    """
    import ctypes

    from gi.repository import GLib  # noqa: F401

    for name in ("libintl-8.dll", "intl-8.dll", "intl.dll"):
        try:
            libintl = ctypes.CDLL(name)
            break
        except OSError:
            continue
    else:
        print("Cannot find libintl, the interface will not be translated.")
        return

    domain = GETTEXT_PACKAGE.encode()

    # The wide variant copes with non-ASCII install paths
    if hasattr(libintl, "wbindtextdomain"):
        libintl.wbindtextdomain.argtypes = [ctypes.c_char_p, ctypes.c_wchar_p]
        libintl.wbindtextdomain.restype = ctypes.c_wchar_p
        libintl.wbindtextdomain(domain, localedir)
    else:
        libintl.bindtextdomain.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        libintl.bindtextdomain.restype = ctypes.c_char_p
        libintl.bindtextdomain(domain, localedir.encode("mbcs"))

    libintl.bind_textdomain_codeset.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    libintl.bind_textdomain_codeset.restype = ctypes.c_char_p
    libintl.bind_textdomain_codeset(domain, b"UTF-8")

    libintl.textdomain.argtypes = [ctypes.c_char_p]
    libintl.textdomain.restype = ctypes.c_char_p
    libintl.textdomain(domain)
