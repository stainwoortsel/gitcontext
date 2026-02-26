"""Index management for GitContext."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..utils.logger import Logger
from ..utils.errors import StorageError
from .filesystem import FileSystemStorage


class IndexManager:
    """Manages the GitContext index (branches, current state)."""

    def __init__(self, storage: FileSystemStorage):
        self.storage = storage
        self.index_path = ['index.yaml']
        self._cache = None

    def load(self) -> Dict[str, Any]:
        """Load index from disk."""
        if self._cache is not None:
            return self._cache

        try:
            if self.storage.exists(*self.index_path):
                self._cache = self.storage.load_yaml(*self.index_path)
            else:
                self._cache = self._create_default()

            return self._cache
        except Exception as e:
            raise StorageError(f"Failed to load index: {e}")

    def save(self) -> None:
        """Save index to disk."""
        if self._cache is None:
            return

        try:
            self.storage.save_yaml(self._cache, *self.index_path)
        except Exception as e:
            raise StorageError(f"Failed to save index: {e}")

    def _create_default(self) -> Dict[str, Any]:
        """Create default index structure."""
        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'current_branch': 'main',
            'branches': {
                'main': {
                    'created': datetime.now().isoformat(),
                    'last_modified': datetime.now().isoformat(),
                    'current_commit': None,
                    'commits': [],
                    'metadata': {}
                }
            }
        }

    def get_current_branch(self) -> str:
        """Get current branch name."""
        return self.load().get('current_branch', 'main')

    def set_current_branch(self, branch: str) -> None:
        """Set current branch."""
        index = self.load()
        if branch not in index['branches']:
            raise StorageError(f"Branch '{branch}' not found")
        index['current_branch'] = branch
        index['last_modified'] = datetime.now().isoformat()
        self._cache = index
        self.save()

    def get_branch(self, name: str) -> Optional[Dict[str, Any]]:
        """Get branch info by name."""
        return self.load()['branches'].get(name)

    def get_all_branches(self) -> Dict[str, Dict[str, Any]]:
        """Get all branches."""
        return self.load()['branches']

    def create_branch(self, name: str, from_branch: str = 'main') -> None:
        """Create a new branch."""
        index = self.load()

        if name in index['branches']:
            raise StorageError(f"Branch '{name}' already exists")

        if from_branch not in index['branches']:
            raise StorageError(f"Source branch '{from_branch}' not found")

        source = index['branches'][from_branch]

        index['branches'][name] = {
            'created': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'parent': from_branch,
            'current_commit': source['current_commit'],
            'commits': source['commits'].copy(),
            'metadata': {}
        }

        index['last_modified'] = datetime.now().isoformat()
        self._cache = index
        self.save()

    def delete_branch(self, name: str) -> None:
        """Delete a branch."""
        index = self.load()

        if name not in index['branches']:
            raise StorageError(f"Branch '{name}' not found")

        if name == 'main':
            raise StorageError("Cannot delete main branch")

        if name == index['current_branch']:
            raise StorageError("Cannot delete current branch")

        del index['branches'][name]
        index['last_modified'] = datetime.now().isoformat()
        self._cache = index
        self.save()

    def add_commit(self, branch: str, commit_id: str) -> None:
        """Add a commit to branch."""
        index = self.load()

        if branch not in index['branches']:
            raise StorageError(f"Branch '{branch}' not found")

        branch_data = index['branches'][branch]
        branch_data['commits'].append(commit_id)
        branch_data['current_commit'] = commit_id
        branch_data['last_modified'] = datetime.now().isoformat()

        index['last_modified'] = datetime.now().isoformat()
        self._cache = index
        self.save()

    def get_commits(self, branch: str) -> List[str]:
        """Get list of commit IDs for a branch."""
        branch_data = self.get_branch(branch)
        return branch_data.get('commits', []) if branch_data else []

    def get_current_commit(self, branch: Optional[str] = None) -> Optional[str]:
        """Get current commit for a branch."""
        if branch is None:
            branch = self.get_current_branch()

        branch_data = self.get_branch(branch)
        return branch_data.get('current_commit') if branch_data else None

    def clear_cache(self):
        """Clear in-memory cache."""
        self._cache = None
