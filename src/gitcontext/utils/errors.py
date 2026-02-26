"""Custom exceptions for GitContext."""

class GitContextError(Exception):
    """Base exception for all GitContext errors."""
    pass

class NotInitializedError(GitContextError):
    """Raised when GitContext is not initialized in the repository."""
    pass

class BranchError(GitContextError):
    """Raised for branch-related errors."""
    pass

class CommitError(GitContextError):
    """Raised for commit-related errors."""
    pass

class MergeError(GitContextError):
    """Raised for merge-related errors."""
    pass

class LLMError(GitContextError):
    """Raised for LLM-related errors."""
    pass

class StorageError(GitContextError):
    """Raised for storage-related errors."""
    pass

class GitIntegrationError(GitContextError):
    """Raised for Git integration errors."""
    pass

class ConfigurationError(GitContextError):
    """Raised for configuration errors."""
    pass
