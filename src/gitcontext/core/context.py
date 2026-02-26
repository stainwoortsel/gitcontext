"""Main GitContext implementation."""

from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import hashlib
import uuid

from ..utils.logger import Logger
from ..utils.config import Config
from ..utils.errors import (
    NotInitializedError, BranchError, CommitError, MergeError
)
from ..storage.filesystem import FileSystemStorage
from ..storage.index import IndexManager
from ..git.integration import GitIntegration
from ..llm import create_provider
from ..models.ota import OTALog
from ..models.types import ContextCommit, SquashResult, Alternative


class GitContext:
    """Main GitContext class for managing AI context."""

    def __init__(
        self,
        repo_path: Union[str, Path] = ".",
        config: Optional[Config] = None
    ):
        self.repo_path = Path(repo_path).absolute()
        self.config = config or Config.load()

        # Initialize components
        self.storage = FileSystemStorage(
            self.repo_path,
            self.config.storage.context_dir
        )
        self.index = IndexManager(self.storage)
        self.git = GitIntegration(self.repo_path)

        # Initialize LLM provider
        self.llm = create_provider(
            provider=self.config.llm.provider,
            model=self.config.llm.model,
            api_key=self.config.llm.api_key
        )

        Logger.debug(f"GitContext initialized for {self.repo_path}")

    def init(self) -> None:
        """Initialize GitContext in repository."""
        if self.storage.exists():
            Logger.info("GitContext already initialized")
            return

        # Create directory structure
        dirs = [
            "contexts/main/current",
            "contexts/main/history",
            "contexts/branches",
            "archive",
            "temp"
        ]
        for d in dirs:
            self.storage.ensure_dir(*d.split('/'))

        # Create initial commit
        initial_commit = ContextCommit(
            id=self._generate_commit_id(),
            message="Initial context",
            timestamp=datetime.now(),
            decisions=["Repository initialized with GitContext"]
        )

        self._save_commit(initial_commit, "main")
        self.index.add_commit("main", initial_commit.id)

        # Create gitignore
        gitignore = self.storage.get_path(".gitignore")
        if not gitignore.exists():
            with open(gitignore, 'w') as f:
                f.write("temp/\n*.log\n*.tmp\n")

        Logger.success(f"GitContext initialized at {self.storage.context_path}")
        Logger.info(f"Initial commit: {initial_commit.short_id()}")

    def branch(self, name: str, from_branch: Optional[str] = None) -> None:
        """Create a new context branch."""
        if not name or '/' in name or '\\' in name:
            raise BranchError(f"Invalid branch name: {name}")

        source = from_branch or self.index.get_current_branch()
        self.index.create_branch(name, source)

        # Create branch directories
        self.storage.ensure_dir("contexts", "branches", name, "current")
        self.storage.ensure_dir("contexts", "branches", name, "history")
        self.storage.ensure_dir("contexts", "branches", name, "ota-logs")

        Logger.success(f"Created branch: {name} (from {source})")

    def checkout(self, branch: str) -> None:
        """Switch to a different branch."""
        self.index.set_current_branch(branch)
        Logger.success(f"Switched to branch: {branch}")

    def commit(
        self,
        message: str,
        ota_logs: Optional[List[OTALog]] = None,
        decisions: Optional[List[str]] = None
    ) -> str:
        """Create a new commit."""
        current_branch = self.index.get_current_branch()
        current_commit = self.index.get_current_commit(current_branch)

        # Get files snapshot
        tracked_files = self.git.get_tracked_files()
        files_snapshot = self.storage.get_files_snapshot(tracked_files)

        # Analyze OTA logs if provided
        alternatives = []
        metadata = {}

        if ota_logs:
            Logger.info(f"Analyzing {len(ota_logs)} OTA logs...")
            analysis = self.llm.analyze_ota_logs(ota_logs)
            decisions = decisions or analysis.get("decisions", [])
            alternatives = [
                Alternative(**alt) if isinstance(alt, dict) else alt
                for alt in analysis.get("alternatives", [])
            ]
            metadata["insights"] = analysis.get("insights", [])

        # Create commit
        commit = ContextCommit(
            id=self._generate_commit_id(),
            message=message,
            timestamp=datetime.now(),
            parent=current_commit,
            decisions=decisions or [],
            alternatives=alternatives,
            ota_logs=ota_logs or [],
            files_snapshot=files_snapshot,
            metadata=metadata
        )

        # Save commit
        self._save_commit(commit, current_branch)
        self.index.add_commit(current_branch, commit.id)

        # Save OTA logs separately if any
        if ota_logs:
            self._save_ota_logs(ota_logs, current_branch, commit.id)

        # Auto-git commit if configured
        if self.config.git.auto_commit:
            self._auto_git_commit(message)

        Logger.success(f"Commit {commit.short_id()}: {message}")
        if decisions:
            Logger.info(f"  Decisions: {len(decisions)}")
        if ota_logs:
            Logger.info(f"  OTA logs: {len(ota_logs)}")

        return commit.id

    def merge(self, branch: str, squash: bool = True) -> SquashResult:
        """Merge a branch into current branch."""
        current_branch = self.index.get_current_branch()

        if branch == current_branch:
            raise MergeError("Cannot merge a branch into itself")

        branch_data = self.index.get_branch(branch)
        if not branch_data:
            raise MergeError(f"Branch '{branch}' not found")

        # Get branch commits
        commits = self._get_branch_commits(branch)

        if squash:
            # Get current context for analysis
            current_context = self._get_current_context()

            Logger.info(f"Analyzing branch '{branch}' with {len(commits)} commits...")

            # Analyze and squash
            result = self.llm.squash_branch_history(
                branch_name=branch,
                commits=commits,
                current_context=current_context
            )

            # Archive branch
            self._archive_branch(branch, commits, result)

            # Apply squash result
            self._apply_squash_result(result)

            # Delete branch
            self.index.delete_branch(branch)

            # Clean up branch directory
            self.storage.delete("contexts", "branches", branch)

            Logger.success(f"Merged {branch} → {current_branch} (squashed)")
            Logger.info(f"  Decisions: {len(result.decisions)}")
            Logger.info(f"  Rejected: {len(result.rejected_alternatives)}")
            Logger.info(f"  Insights: {len(result.key_insights)}")
            Logger.info(f"  Original commits: {result.original_commits} → summarized")

            return result
        else:
            # Simple merge - just add all commits
            for commit in commits:
                self._save_commit(commit, current_branch)
                self.index.add_commit(current_branch, commit.id)

            self.index.delete_branch(branch)
            self.storage.delete("contexts", "branches", branch)

            Logger.success(f"Merged {branch} → {current_branch} (simple)")

            return SquashResult(
                decisions=[],
                rejected_alternatives=[],
                key_insights=[],
                architecture_summary="Simple merge completed",
                ota_count=0,
                original_commits=len(commits),
                branch_name=branch
            )

    def log(self, branch: Optional[str] = None, limit: int = 10) -> List[ContextCommit]:
        """Show commit history."""
        target_branch = branch or self.index.get_current_branch()
        commit_ids = self.index.get_commits(target_branch)

        commits = []
        for commit_id in commit_ids[-limit:]:
            commit = self._load_commit(commit_id, target_branch)
            if commit:
                commits.append(commit)

        return commits

    def status(self) -> Dict[str, Any]:
        """Get current status."""
        current_branch = self.index.get_current_branch()
        branch_data = self.index.get_branch(current_branch)

        # Get latest commit
        latest_commit = None
        if branch_data and branch_data.get('current_commit'):
            latest_commit = self._load_commit(
                branch_data['current_commit'],
                current_branch
            )

        # Check for uncommitted changes
        tracked_files = self.git.get_tracked_files()
        current_files = self.storage.get_files_snapshot(tracked_files)

        uncommitted = False
        if latest_commit:
            uncommitted = current_files != latest_commit.files_snapshot

        # Also check for pending OTA logs
        temp_dir = self.storage.get_path("temp")
        pending_ota = 0
        if temp_dir.exists():
            pending_ota = len(list(temp_dir.glob("ota_*.json")))

        return {
            "current_branch": current_branch,
            "commits": len(branch_data.get('commits', [])) if branch_data else 0,
            "latest_commit": latest_commit.message if latest_commit else None,
            "latest_commit_id": latest_commit.short_id() if latest_commit else None,
            "uncommitted_changes": uncommitted,
            "pending_ota_logs": pending_ota,
            "all_branches": list(self.index.get_all_branches().keys())
        }

    def _generate_commit_id(self) -> str:
        """Generate a unique commit ID."""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}{uuid.uuid4()}".encode()
        ).hexdigest()[:12]

    def _save_commit(self, commit: ContextCommit, branch: str) -> None:
        """Save a commit to disk."""
        if branch == "main":
            path = ["contexts", "main", "history", f"commit_{commit.id}", "commit.json"]
        else:
            path = ["contexts", "branches", branch, "history", f"commit_{commit.id}", "commit.json"]

        self.storage.save_json(commit.to_dict(), *path)

    def _load_commit(self, commit_id: str, branch: str) -> Optional[ContextCommit]:
        """Load a commit from disk."""
        if branch == "main":
            path = ["contexts", "main", "history", f"commit_{commit_id}", "commit.json"]
        else:
            path = ["contexts", "branches", branch, "history", f"commit_{commit_id}", "commit.json"]

        if not self.storage.exists(*path):
            return None

        data = self.storage.load_json(*path)
        return ContextCommit.from_dict(data)

    def _save_ota_logs(self, logs: List[OTALog], branch: str, commit_id: str) -> None:
        """Save OTA logs for a commit."""
        if branch == "main":
            path = ["contexts", "main", "ota-logs", f"commit_{commit_id}.json"]
        else:
            path = ["contexts", "branches", branch, "ota-logs", f"commit_{commit_id}.json"]

        data = [log.to_dict() for log in logs]
        self.storage.save_json(data, *path)

    def _get_branch_commits(self, branch: str) -> List[ContextCommit]:
        """Get all commits from a branch."""
        commit_ids = self.index.get_commits(branch)
        commits = []

        for commit_id in commit_ids:
            commit = self._load_commit(commit_id, branch)
            if commit:
                commits.append(commit)

        return commits

    def _get_current_context(self) -> Dict[str, Any]:
        """Get current context summary."""
        current_branch = self.index.get_current_branch()
        current_commit = self.index.get_current_commit(current_branch)

        context = {
            "branch": current_branch,
            "files": self.git.get_tracked_files()[:20],  # First 20 files
        }

        if current_commit:
            commit = self._load_commit(current_commit, current_branch)
            if commit:
                context["latest_commit"] = commit.message
                context["decisions"] = commit.decisions

        return context

    def _archive_branch(
        self,
        branch: str,
        commits: List[ContextCommit],
        result: SquashResult
    ) -> None:
        """Archive a branch before deletion."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_dir = f"archive/{branch}_{timestamp}"

        # Save branch data
        branch_data = {
            "branch": branch,
            "archived_at": datetime.now().isoformat(),
            "commits": [c.to_dict() for c in commits],
            "squash_result": result.to_dict()
        }
        self.storage.save_json(branch_data, archive_dir, "branch.json")

        # Save readable summary
        self.storage.save_text(result.to_markdown(), archive_dir, "summary.md")

        # Copy OTA logs
        all_ota = []
        for commit in commits:
            all_ota.extend([log.to_dict() for log in commit.ota_logs])

        if all_ota:
            self.storage.save_json(all_ota, archive_dir, "ota_logs.json")

        if self.config.storage.compress_archive:
            # TODO: Implement compression
            pass

    def _apply_squash_result(self, result: SquashResult) -> None:
        """Apply squash result to current branch."""
        current_branch = self.index.get_current_branch()
        current_commit = self.index.get_current_commit(current_branch)

        # Create squash commit
        squash_commit = ContextCommit(
            id=self._generate_commit_id(),
            message=f"🔄 Squash merge: {result.branch_name}",
            timestamp=datetime.now(),
            parent=current_commit,
            decisions=result.decisions,
            alternatives=result.rejected_alternatives,
            ota_logs=[],
            files_snapshot=self.storage.get_files_snapshot(self.git.get_tracked_files()),
            metadata={
                "squash_merge": True,
                "source_branch": result.branch_name,
                "original_commits": result.original_commits,
                "insights": result.key_insights,
                "architecture_summary": result.architecture_summary
            }
        )

        self._save_commit(squash_commit, current_branch)
        self.index.add_commit(current_branch, squash_commit.id)

    def _auto_git_commit(self, message: str) -> None:
        """Automatically commit changes to git."""
        if self.git.has_uncommitted_changes():
            files = self.git.get_modified_files()
            if files:
                Logger.info(f"Auto-committing to git: {len(files)} files")
                self.git.commit(f"GitContext: {message}", files)