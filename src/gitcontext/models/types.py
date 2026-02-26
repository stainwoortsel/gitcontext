"""Core data models for GitContext."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from .ota import OTALog


class Alternative(BaseModel):
    """Represents an alternative approach that was considered but rejected."""

    what: str = Field(..., description="What was considered")
    why_rejected: str = Field(..., description="Why it was rejected")

    def to_dict(self) -> Dict[str, str]:
        return {'what': self.what, 'why_rejected': self.why_rejected}


class ContextCommit(BaseModel):
    """
    Represents a commit in the context history.

    Similar to a Git commit, but stores AI context, decisions, and OTA logs.
    """

    id: str = Field(..., description="Commit ID (hash)")
    message: str = Field(..., description="Commit message")
    timestamp: datetime = Field(default_factory=datetime.now)
    parent: Optional[str] = Field(None, description="Parent commit ID")

    decisions: List[str] = Field(default_factory=list, description="Key decisions made")
    alternatives: List[Alternative] = Field(default_factory=list, description="Rejected alternatives")
    ota_logs: List[OTALog] = Field(default_factory=list, description="OTA logs in this commit")

    files_snapshot: Dict[str, str] = Field(
        default_factory=dict,
        description="File path -> content hash"
    )

    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'parent': self.parent,
            'decisions': self.decisions,
            'alternatives': [a.to_dict() for a in self.alternatives],
            'ota_logs': [log.to_dict() for log in self.ota_logs],
            'files_snapshot': self.files_snapshot,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextCommit':
        """Create from dictionary."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        # Convert alternatives
        if 'alternatives' in data:
            data['alternatives'] = [
                Alternative(**alt) if isinstance(alt, dict) else alt
                for alt in data['alternatives']
            ]

        # Convert OTA logs
        if 'ota_logs' in data:
            data['ota_logs'] = [
                OTALog.from_dict(log) if isinstance(log, dict) else log
                for log in data['ota_logs']
            ]

        return cls(**data)

    def short_id(self) -> str:
        """Get short version of commit ID."""
        return self.id[:8]


class SquashResult(BaseModel):
    """
    Result of squashing a branch's history.

    Contains the distilled information from many commits.
    """

    decisions: List[str] = Field(default_factory=list)
    rejected_alternatives: List[Alternative] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    architecture_summary: str = ""

    ota_count: int = 0
    original_commits: int = 0
    branch_name: str = ""

    merged_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'decisions': self.decisions,
            'rejected_alternatives': [a.to_dict() for a in self.rejected_alternatives],
            'key_insights': self.key_insights,
            'architecture_summary': self.architecture_summary,
            'ota_count': self.ota_count,
            'original_commits': self.original_commits,
            'branch_name': self.branch_name,
            'merged_at': self.merged_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Format as markdown for documentation."""
        lines = [
            f"# Squash Merge: {self.branch_name}",
            "",
            f"Merged: {self.merged_at.strftime('%Y-%m-%d %H:%M')}",
            f"Original commits: {self.original_commits} → summarized",
            "",
            "## 📊 Final Decisions",
        ]

        for d in self.decisions:
            lines.append(f"- {d}")

        lines.extend(["", "## ❌ Rejected Alternatives"])
        for alt in self.rejected_alternatives:
            lines.append(f"- **{alt.what}**: {alt.why_rejected}")

        lines.extend(["", "## 💡 Key Insights"])
        for insight in self.key_insights:
            lines.append(f"- {insight}")

        lines.extend(["", "## 🏗️ Architecture Summary", self.architecture_summary])

        return "\n".join(lines)


class BranchInfo(BaseModel):
    """Information about a context branch."""

    name: str
    created: datetime
    last_modified: datetime
    current_commit: Optional[str] = None
    commits: List[str] = Field(default_factory=list)
    parent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StatusInfo(BaseModel):
    """Current status information."""

    current_branch: str
    commits: int
    latest_commit: Optional[str] = None
    latest_commit_id: Optional[str] = None
    uncommitted_changes: bool = False
    all_branches: List[str] = Field(default_factory=list)
