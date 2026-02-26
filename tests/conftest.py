"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from gitcontext import GitContext
from gitcontext.utils.config import Config


@pytest.fixture
def temp_repo():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def gitcontext(temp_repo):
    """Create a GitContext instance with mock LLM."""
    config = Config()
    config.llm.provider = "mock"
    gc = GitContext(temp_repo, config)
    gc.init()
    return gc


@pytest.fixture
def sample_ota_log():
    """Create a sample OTA log."""
    from gitcontext.models.ota import OTALog
    return OTALog(
        thought="Need to implement authentication",
        action="Added JWT middleware",
        result="Authentication working",
        files_affected=["auth.py", "main.py"]
    )


@pytest.fixture
def sample_commit(gitcontext, sample_ota_log):
    """Create a sample commit."""
    return gitcontext.commit(
        message="Test commit",
        ota_logs=[sample_ota_log],
        decisions=["Use JWT for auth"]
    )
