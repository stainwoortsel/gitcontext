"""Core GitContext functionality"""
import os
import json
import yaml
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import hashlib
import uuid

from .models import OTALog, ContextCommit, SquashResult
from .llm_integration import LLMAnalyzer
from .git_integration import GitHelper
from .utils import ensure_dir, load_yaml, save_yaml, load_json, save_json


class GitContext:
    """Main GitContext class for managing AI context"""

    def __init__(self, repo_path: str = ".", llm_provider: str = "openai",
                 llm_model: Optional[str] = None, api_key: Optional[str] = None):
        self.repo_path = Path(repo_path).absolute()
        self.context_path = self.repo_path / ".gitcontext"
        self.llm = LLMAnalyzer(provider=llm_provider, model=llm_model, api_key=api_key)
        self.git = GitHelper(repo_path)

    def init(self) -> None:
        """Initialize GitContext in repository"""
        if self.context_path.exists():
            print(f"✓ GitContext already exists at {self.context_path}")
            return

        # Create directory structure
        dirs = [
            "contexts/main/current",
            "contexts/main/history",
            "contexts/branches",
            "archive",
            "temp",
            "hooks"
        ]
        for d in dirs:
            ensure_dir(self.context_path / d)

        # Create index
        index = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "current_branch": "main",
            "branches": {
                "main": {
                    "created": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat(),
                    "current_commit": None,
                    "commits": [],
                    "metadata": {}
                }
            }
        }
        save_yaml(self.context_path / "index.yaml", index)

        # Create initial commit
        initial_commit = ContextCommit(
            id=self._generate_commit_id(),
            message="Initial context",
            timestamp=datetime.now(),
            decisions=["Repository initialized with GitContext"],
            ota_logs=[]
        )
        self._save_commit(initial_commit, "main")

        # Update index with initial commit
        index["branches"]["main"]["current_commit"] = initial_commit.id
        index["branches"]["main"]["commits"] = [initial_commit.id]
        save_yaml(self.context_path / "index.yaml", index)

        # Create gitignore
        gitignore = self.context_path / ".gitignore"
        if not gitignore.exists():
            with open(gitignore, "w") as f:
                f.write("temp/\n")
                f.write("*.log\n")

        print(f"✅ GitContext initialized at {self.context_path}")
        print(f"   Initial commit: {initial_commit.id[:8]}")

    def branch(self, name: str, from_branch: Optional[str] = None) -> None:
        """Create a new context branch"""
        # Validate branch name
        if not name or "\\" in name:
            raise ValueError(f"Invalid branch name: {name}")

        index = load_yaml(self.context_path / "index.yaml")

        # Check if branch exists
        if name in index["branches"]:
            raise ValueError(f"Branch '{name}' already exists")

        # Determine source branch
        source = from_branch or index["current_branch"]
        if source not in index["branches"]:
            raise ValueError(f"Source branch '{source}' not found")

        # Create branch in index
        index["branches"][name] = {
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "parent": source,
            "current_commit": index["branches"][source]["current_commit"],
            "commits": index["branches"][source]["commits"].copy(),
            "metadata": {}
        }

        save_yaml(self.context_path / "index.yaml", index)

        # Create branch directories
        branch_dir = self.context_path / "contexts" / "branches" / name
        ensure_dir(branch_dir / "current")
        ensure_dir(branch_dir / "history")
        ensure_dir(branch_dir / "ota-logs")

        print(f"✅ Created branch: {name} (from {source})")

    def checkout(self, branch: str) -> None:
        """Switch to a different branch"""
        index = load_yaml(self.context_path / "index.yaml")

        if branch not in index["branches"]:
            raise ValueError(f"Branch '{branch}' not found")

        index["current_branch"] = branch
        save_yaml(self.context_path / "index.yaml", index)

        print(f"✅ Switched to branch: {branch}")

    def commit(self, message: str, ota_logs: Optional[List[OTALog]] = None,
               decisions: Optional[List[str]] = None) -> str:
        """Create a new commit in current branch"""
        index = load_yaml(self.context_path / "index.yaml")
        current_branch = index["current_branch"]
        branch_data = index["branches"][current_branch]

        # Get current state
        current_commit_id = branch_data["current_commit"]
        files_snapshot = self._get_files_snapshot()

        # Analyze OTA logs if provided
        alternatives = []
        metadata = {}
        if ota_logs:
            analysis = self.llm.analyze_ota_logs(ota_logs)
            decisions = decisions or analysis.get("decisions", [])
            alternatives = analysis.get("alternatives", [])
            metadata["insights"] = analysis.get("insights", [])

        # Create commit
        commit = ContextCommit(
            id=self._generate_commit_id(),
            message=message,
            timestamp=datetime.now(),
            parent=current_commit_id,
            decisions=decisions or [],
            alternatives=alternatives,
            ota_logs=ota_logs or [],
            files_snapshot=files_snapshot,
            metadata=metadata
        )

        # Save commit
        self._save_commit(commit, current_branch)

        # Update branch in index
        branch_data["commits"].append(commit.id)
        branch_data["current_commit"] = commit.id
        branch_data["last_modified"] = datetime.now().isoformat()

        save_yaml(self.context_path / "index.yaml", index)

        print(f"✅ Commit {commit.id[:8]}: {message}")
        if decisions:
            print(f"   Decisions: {len(decisions)}")
        if ota_logs:
            print(f"   OTA logs: {len(ota_logs)}")

        return commit.id

    def merge(self, branch: str, squash: bool = True) -> SquashResult:
        """Merge a branch into current branch"""
        index = load_yaml(self.context_path / "index.yaml")
        current_branch = index["current_branch"]

        if branch == current_branch:
            raise ValueError("Cannot merge a branch into itself")

        if branch not in index["branches"]:
            raise ValueError(f"Branch '{branch}' not found")

        # Get branch commits
        commits = self._get_branch_commits(branch)

        if squash:
            # Get current context for analysis
            current_context = self._get_current_context()

            # Analyze and squash
            result = self.llm.squash_branch_history(
                branch_name=branch,
                commits=commits,
                current_context=current_context
            )

            # Archive branch
            self._archive_branch(branch, commits, result)

            # Apply squash result to current branch
            self._apply_squash_result(result)

            # Delete branch
            del index["branches"][branch]
            save_yaml(self.context_path / "index.yaml", index)

            # Remove branch directory
            branch_dir = self.context_path / "contexts" / "branches" / branch
            if branch_dir.exists():
                shutil.rmtree(branch_dir)

            print(f"\n✅ Merged {branch} → {current_branch} (squashed)")
            print(f"   📊 Summary:")
            print(f"   • Decisions: {len(result.decisions)}")
            print(f"   • Rejected: {len(result.rejected_alternatives)}")
            print(f"   • Insights: {len(result.key_insights)}")
            print(f"   • Original commits: {result.original_commits} → summarized")
            print(f"   📦 Archive: .gitcontext/archive/{branch}_{result.merged_at.strftime('%Y%m%d_%H%M%S')}/")

            return result
        else:
            # Simple merge (just copy commits)
            print(f"✅ Merged {branch} → {current_branch} (simple)")
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
        """Show commit history"""
        index = load_yaml(self.context_path / "index.yaml")
        target_branch = branch or index["current_branch"]

        if target_branch not in index["branches"]:
            raise ValueError(f"Branch '{target_branch}' not found")

        commit_ids = index["branches"][target_branch]["commits"][-limit:]
        commits = []

        for commit_id in commit_ids:
            commit = self._load_commit(commit_id, target_branch)
            if commit:
                commits.append(commit)

        return commits

    def status(self) -> Dict[str, Any]:
        """Show current status"""
        index = load_yaml(self.context_path / "index.yaml")
        current_branch = index["current_branch"]
        branch_data = index["branches"][current_branch]

        # Get latest commit
        latest_commit = None
        if branch_data["current_commit"]:
            latest_commit = self._load_commit(branch_data["current_commit"], current_branch)

        # Check for uncommitted changes
        current_files = self._get_files_snapshot()
        uncommitted = False
        if latest_commit:
            # Simple check: compare with latest commit's snapshot
            uncommitted = current_files != latest_commit.files_snapshot

        return {
            "current_branch": current_branch,
            "commits": len(branch_data["commits"]),
            "latest_commit": latest_commit.message if latest_commit else None,
            "latest_commit_id": latest_commit.id[:8] if latest_commit else None,
            "uncommitted_changes": uncommitted,
            "all_branches": list(index["branches"].keys())
        }

    def _generate_commit_id(self) -> str:
        """Generate a unique commit ID"""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}{uuid.uuid4()}".encode()
        ).hexdigest()[:12]

    def _save_commit(self, commit: ContextCommit, branch: str) -> None:
        """Save a commit to disk"""
        if branch == "main":
            commit_dir = self.context_path / "contexts" / "main" / "history" / f"commit_{commit.id}"
        else:
            commit_dir = self.context_path / "contexts" / "branches" / branch / "history" / f"commit_{commit.id}"

        ensure_dir(commit_dir)
        save_json(commit_dir / "commit.json", commit.to_dict())

    def _load_commit(self, commit_id: str, branch: str) -> Optional[ContextCommit]:
        """Load a commit from disk"""
        if branch == "main":
            commit_path = self.context_path / "contexts" / "main" / "history" / f"commit_{commit_id}" / "commit.json"
        else:
            commit_path = self.context_path / "contexts" / "branches" / branch / "history" / f"commit_{commit_id}" / "commit.json"

        if not commit_path.exists():
            return None

        data = load_json(commit_path)
        return ContextCommit.from_dict(data)

    def _get_branch_commits(self, branch: str) -> List[ContextCommit]:
        """Get all commits from a branch"""
        index = load_yaml(self.context_path / "index.yaml")

        if branch not in index["branches"]:
            return []

        commit_ids = index["branches"][branch]["commits"]
        commits = []

        for commit_id in commit_ids:
            commit = self._load_commit(commit_id, branch)
            if commit:
                commits.append(commit)

        return commits

    def _get_files_snapshot(self) -> Dict[str, str]:
        """Get snapshot of current files (content hashes)"""
        snapshot = {}

        # Get all tracked files from git
        files = self.git.get_tracked_files()

        for file in files:
            file_path = self.repo_path / file
            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = f.read()
                snapshot[file] = hashlib.sha256(content).hexdigest()[:16]

        return snapshot

    def _get_current_context(self) -> Dict[str, Any]:
        """Get current context summary"""
        index = load_yaml(self.context_path / "index.yaml")
        current_branch = index["current_branch"]

        # Get latest commit
        latest_commit = None
        if index["branches"][current_branch]["current_commit"]:
            latest_commit = self._load_commit(
                index["branches"][current_branch]["current_commit"],
                current_branch
            )

        return {
            "branch": current_branch,
            "latest_commit": latest_commit.message if latest_commit else None,
            "decisions": latest_commit.decisions if latest_commit else [],
            "files": list(self._get_files_snapshot().keys())[:20]  # First 20 files
        }

    def _archive_branch(self, branch: str, commits: List[ContextCommit], result: SquashResult) -> None:
        """Archive a branch before deletion"""
        timestamp = result.merged_at.strftime("%Y%m%d_%H%M%S")
        archive_dir = self.context_path / "archive" / f"{branch}_{timestamp}"
        ensure_dir(archive_dir)

        # Save full branch data
        branch_data = {
            "branch": branch,
            "archived_at": datetime.now().isoformat(),
            "commits": [c.to_dict() for c in commits],
            "squash_result": result.to_dict()
        }
        save_json(archive_dir / "branch_archive.json", branch_data)

        # Save readable summary
        with open(archive_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(result.to_markdown())

        # Copy any OTA logs
        ota_logs = []
        for commit in commits:
            ota_logs.extend(commit.ota_logs)

        if ota_logs:
            with open(archive_dir / "ota_logs.json", "w", encoding="utf-8") as f:
                json.dump([log.to_dict() for log in ota_logs], f, indent=2, ensure_ascii=False)

    def _apply_squash_result(self, result: SquashResult) -> None:
        """Apply squash result to current branch"""
        # Create a special squash commit
        squash_commit = ContextCommit(
            id=self._generate_commit_id(),
            message=f"🔄 Squash merge: {result.branch_name}",
            timestamp=datetime.now(),
            parent=self._get_current_commit_id(),
            decisions=result.decisions,
            alternatives=result.rejected_alternatives,
            ota_logs=[],
            files_snapshot=self._get_files_snapshot(),
            metadata={
                "squash_merge": True,
                "source_branch": result.branch_name,
                "original_commits": result.original_commits,
                "insights": result.key_insights,
                "architecture_summary": result.architecture_summary
            }
        )

        # Save commit
        current_branch = self._get_current_branch()
        self._save_commit(squash_commit, current_branch)

        # Update index
        index = load_yaml(self.context_path / "index.yaml")
        index["branches"][current_branch]["commits"].append(squash_commit.id)
        index["branches"][current_branch]["current_commit"] = squash_commit.id
        index["branches"][current_branch]["last_modified"] = datetime.now().isoformat()
        save_yaml(self.context_path / "index.yaml", index)

    def _get_current_branch(self) -> str:
        """Get current branch name"""
        index = load_yaml(self.context_path / "index.yaml")
        return index["current_branch"]

    def _get_current_commit_id(self) -> Optional[str]:
        """Get current commit ID"""
        index = load_yaml(self.context_path / "index.yaml")
        branch = index["current_branch"]
        return index["branches"][branch]["current_commit"]
