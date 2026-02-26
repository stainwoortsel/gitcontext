"""Unit tests for data models."""

import pytest
from datetime import datetime
from gitcontext.models.ota import OTALog
from gitcontext.models.types import ContextCommit, Alternative, SquashResult


def test_ota_log_creation():
    """Test creating an OTA log."""
    log = OTALog(
        thought="Test thought",
        action="Test action",
        result="Test result",
        files_affected=["file1.py", "file2.py"]
    )

    assert log.thought == "Test thought"
    assert log.action == "Test action"
    assert log.result == "Test result"
    assert len(log.files_affected) == 2
    assert log.id is not None
    assert isinstance(log.timestamp, datetime)


def test_ota_log_serialization():
    """Test OTA log serialization."""
    log = OTALog(
        thought="Test",
        action="Test",
        result="Test"
    )

    data = log.to_dict()
    assert data['thought'] == "Test"

    restored = OTALog.from_dict(data)
    assert restored.thought == log.thought
    assert restored.action == log.action


def test_alternative_model():
    """Test Alternative model."""
    alt = Alternative(
        what="Use MongoDB",
        why_rejected="Need ACID transactions"
    )

    assert alt.what == "Use MongoDB"
    assert alt.why_rejected == "Need ACID transactions"

    data = alt.to_dict()
    assert data['what'] == "Use MongoDB"


def test_context_commit():
    """Test ContextCommit model."""
    commit = ContextCommit(
        id="abc123",
        message="Test commit",
        timestamp=datetime.now(),
        decisions=["Decision 1"],
        alternatives=[Alternative(what="Alt", why_rejected="Reason")]
    )

    assert commit.id == "abc123"
    assert commit.short_id() == "abc123"
    assert len(commit.decisions) == 1

    data = commit.to_dict()
    restored = ContextCommit.from_dict(data)
    assert restored.id == commit.id
    assert len(restored.alternatives) == 1


def test_squash_result():
    """Test SquashResult model."""
    result = SquashResult(
        decisions=["Decision 1"],
        rejected_alternatives=[Alternative(what="Alt", why_rejected="Reason")],
        key_insights=["Insight 1"],
        architecture_summary="Summary",
        ota_count=5,
        original_commits=10,
        branch_name="feature/test"
    )

    assert len(result.decisions) == 1
    assert result.original_commits == 10

    md = result.to_markdown()
    assert "# Squash Merge: feature/test" in md
    assert "## 📊 Final Decisions" in md
