"""
GitContext - Git for AI context management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track, version, and manage AI context, thoughts, and decisions alongside your code.

Basic usage:
    >>> from gitcontext import GitContext
    >>> gc = GitContext(".")
    >>> gc.init()
    >>> gc.branch("feature/auth")
    >>> gc.commit("Added JWT authentication")

:copyright: (c) 2024 by Your Name
:license: MIT, see LICENSE for more details.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.context import GitContext
from .models.ota import OTALog
from .models.types import ContextCommit, SquashResult

__all__ = [
    "GitContext",
    "OTALog",
    "ContextCommit",
    "SquashResult",
]