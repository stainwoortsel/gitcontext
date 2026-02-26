"""Git integration helpers"""
import subprocess
from pathlib import Path
from typing import List, Optional


class GitHelper:
    """Helper for Git operations"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).absolute()

    def get_tracked_files(self) -> List[str]:
        """Get list of tracked files in repository"""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [f for f in result.stdout.split("\n") if f]
        except subprocess.CalledProcessError:
            return []

    def get_current_branch(self) -> Optional[str]:
        """Get current git branch name"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() or None
        except subprocess.CalledProcessError:
            return None

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a file from git"""
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:{file_path}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None

    def get_modified_files(self) -> List[str]:
        """Get list of modified files"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = []
            for line in result.stdout.split("\n"):
                if line and len(line) > 3:
                    # Status format: "XY filename"
                    files.append(line[3:])
            return files
        except subprocess.CalledProcessError:
            return []

    def get_commit_message(self, commit_hash: str) -> Optional[str]:
        """Get commit message for a hash"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
