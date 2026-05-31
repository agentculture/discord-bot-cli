"""Entry point for ``python -m discord_bot_cli``."""

from __future__ import annotations

import sys

from discord_bot_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
