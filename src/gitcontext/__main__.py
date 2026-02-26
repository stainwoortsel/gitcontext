#!/usr/bin/env python3
"""
GitContext CLI entry point.
Allows running with `python -m gitcontext`
"""

import sys
from .cli.main import cli

if __name__ == "__main__":
    sys.exit(cli())
    