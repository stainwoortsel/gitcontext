"""GitContext - Git for AI context management"""

from .core import GitContext
from .models import OTALog, ContextCommit, SquashResult

__version__ = "0.1.0"
__all__ = ["GitContext", "OTALog", "ContextCommit", "SquashResult"]
