# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry script of the Windows executable, see blanket.spec"""

import sys

from blanket.__main__ import run

sys.exit(run())
