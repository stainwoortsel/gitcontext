"""Git integration for GitContext."""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from ..utils.logger import Logger
from ..utils.errors import GitIntegrationError


class GitIntegration:
    """Handles interaction with Git."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def _run_git(self, args: List[str]) -> str:
        """Run git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            Logger.error(f"Git command failed: {' '.join(args)}")
            Logger.error(f"Error: {e.stderr}")
            raise GitIntegrationError(f"Git command failed: {e.stderr}")

    def is_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            self._run_git(["rev-parse", "--git-dir"])
            return True
        except GitIntegrationError:
            return False

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name."""
        try:
            return self._run_git(["branch", "--show-current"])
        except GitIntegrationError:
            return None

    def get_tracked_files(self) -> List[str]:
        """Get list of tracked files."""
        try:
            output = self._run_git(["ls-files"])
            return [f for f in output.split('\n') if f]
        except GitIntegrationError:
            return []

    def get_modified_files(self) -> List[str]:
        """Get list of modified files."""
        try:
            output = self._run_git(["status", "--porcelain"])
            files = []
            for line in output.split('\n'):
                if line and len(line) > 3:
                    # Status format: "XY filename"
                    files.append(line[3:])
            return files
        except GitIntegrationError:
            return []

    def get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        try:
            output = self._run_git(["diff", "--cached", "--name-only"])
            return [f for f in output.split('\n') if f]
        except GitIntegrationError:
            return []

    def get_file_content(self, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """Get content of a file from git."""
        try:
            return self._run_git(["show", f"{ref}:{file_path}"])
        except GitIntegrationError:
            return None

    def get_commit_hash(self, ref: str = "HEAD") -> Optional[str]:
        """Get commit hash for reference."""
        try:
            return self._run_git(["rev-parse", ref])
        except GitIntegrationError:
            return None

    def get_commit_message(self, commit_hash: str) -> Optional[str]:
        """Get commit message."""
        try:
            return self._run_git(["log", "-1", "--pretty=%B", commit_hash])
        except GitIntegrationError:
            return None

    def get_commit_info(self, commit_hash: str) -> Optional[dict]:
        """Get detailed commit information."""
        try:
            output = self._run_git([
                "show", "--format=%H%n%an%n%ae%n%at%n%s", "--no-patch", commit_hash
            ])
            lines = output.split('\n')
            if len(lines) >= 5:
                return {
                    'hash': lines[0],
                    'author': lines[1],
                    'email': lines[2],
                    'timestamp': datetime.fromtimestamp(int(lines[3])),
                    'message': lines[4]
                }
        except GitIntegrationError:
            pass
        return None

    def get_changes_since(self, commit_hash: str) -> List[str]:
        """Get list of files changed since commit."""
        try:
            output = self._run_git(["diff", "--name-only", commit_hash])
            return [f for f in output.split('\n') if f]
        except GitIntegrationError:
            return []

    def get_current_diff(self, staged: bool = False) -> str:
        """Get current diff."""
        try:
            args = ["diff"]
            if staged:
                args.append("--cached")
            return self._run_git(args)
        except GitIntegrationError:
            return ""

    def stage_file(self, file_path: str) -> bool:
        """Stage a file."""
        try:
            self._run_git(["add", file_path])
            return True
        except GitIntegrationError:
            return False

    def unstage_file(self, file_path: str) -> bool:
        """Unstage a file."""
        try:
            self._run_git(["reset", "HEAD", file_path])
            return True
        except GitIntegrationError:
            return False

    def commit(self, message: str, files: Optional[List[str]] = None) -> Optional[str]:
        """Create a commit."""
        try:
            if files:
                self._run_git(["add"] + files)
            self._run_git(["commit", "-m", message])
            return self.get_commit_hash()
        except GitIntegrationError:
            return None

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """Get remote URL."""
        try:
            return self._run_git(["remote", "get-url", remote])
        except GitIntegrationError:
            return None

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            output = self._run_git(["status", "--porcelain"])
            return bool(output.strip())
        except GitIntegrationError:
            return False
