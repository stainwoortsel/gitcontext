"""Unit tests for storage module."""

import pytest
from pathlib import Path
from gitcontext.storage.filesystem import FileSystemStorage
from gitcontext.storage.index import IndexManager


def test_filesystem_creation(temp_repo):
    """Test filesystem storage creation."""
    storage = FileSystemStorage(temp_repo)
    assert storage.root_path == temp_repo
    assert storage.context_path == temp_repo / ".gitcontext"


def test_ensure_dir(temp_repo):
    """Test directory creation."""
    storage = FileSystemStorage(temp_repo)
    path = storage.ensure_dir("test", "nested", "dir")

    assert path.exists()
    assert path.is_dir()
    assert path == storage.get_path("test", "nested", "dir")


def test_json_operations(temp_repo):
    """Test JSON save/load."""
    storage = FileSystemStorage(temp_repo)
    data = {"key": "value", "number": 42}

    path = storage.save_json(data, "test.json")
    assert path.exists()

    loaded = storage.load_json("test.json")
    assert loaded == data


def test_yaml_operations(temp_repo):
    """Test YAML save/load."""
    storage = FileSystemStorage(temp_repo)
    data = {"key": "value", "list": [1, 2, 3]}

    path = storage.save_yaml(data, "test.yaml")
    assert path.exists()

    loaded = storage.load_yaml("test.yaml")
    assert loaded == data


def test_file_hash(temp_repo):
    """Test file hash calculation."""
    storage = FileSystemStorage(temp_repo)

    # Create a test file
    test_file = temp_repo / "test.txt"
    test_file.write_text("Hello, World!")

    hash1 = storage.get_file_hash(test_file)
    assert len(hash1) == 16  # First 16 chars of SHA256

    # Change file
    test_file.write_text("Hello, World! Changed")
    hash2 = storage.get_file_hash(test_file)
    assert hash1 != hash2


def test_index_manager(temp_repo):
    """Test index manager."""
    storage = FileSystemStorage(temp_repo)
    index = IndexManager(storage)

    # Default state
    assert index.get_current_branch() == "main"

    # Create branch
    index.create_branch("feature/test")
    assert "feature/test" in index.get_all_branches()

    # Switch branch
    index.set_current_branch("feature/test")
    assert index.get_current_branch() == "feature/test"

    # Add commit
    index.add_commit("feature/test", "commit123")
    commits = index.get_commits("feature/test")
    assert "commit123" in commits

    # Delete branch
    index.set_current_branch("main")
    index.delete_branch("feature/test")
    assert "feature/test" not in index.get_all_branches()
