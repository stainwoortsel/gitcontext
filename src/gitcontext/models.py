"""Data models for GitContext"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
import json
import hashlib


@dataclass
class OTALog:
    """Log of AI's thought process during development"""
    thought: str
    action: str
    result: str
    timestamp: datetime = field(default_factory=datetime.now)
    files_affected: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'OTALog':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ContextCommit:
    """A commit in the context history"""
    id: str
    message: str
    timestamp: datetime
    parent: Optional[str] = None
    decisions: List[str] = field(default_factory=list)
    alternatives: List[Dict] = field(default_factory=list)  # [{"what": "...", "why_rejected": "..."}]
    ota_logs: List[OTALog] = field(default_factory=list)
    files_snapshot: Dict[str, str] = field(default_factory=dict)  # filename -> content hash
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['ota_logs'] = [log.to_dict() for log in self.ota_logs]
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'ContextCommit':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['ota_logs'] = [OTALog.from_dict(log) for log in data.get('ota_logs', [])]
        return cls(**data)


@dataclass
class SquashResult:
    """Result of squashing a branch's history"""
    decisions: List[str]
    rejected_alternatives: List[Dict]  # [{"what": "...", "why_rejected": "..."}]
    key_insights: List[str]
    architecture_summary: str
    ota_count: int
    original_commits: int
    branch_name: str
    merged_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['merged_at'] = self.merged_at.isoformat()
        return d

    def to_markdown(self) -> str:
        """Format as markdown for documentation"""
        md = f"# Squash Merge: {self.branch_name}\n\n"
        md += f"Merged: {self.merged_at.strftime('%Y-%m-%d %H:%M')}\n"
        md += f"Original commits: {self.original_commits} → summarized\n\n"

        md += "## 📊 Final Decisions\n"
        for d in self.decisions:
            md += f"- {d}\n"

        md += "\n## ❌ Rejected Alternatives\n"
        for alt in self.rejected_alternatives:
            md += f"- **{alt['what']}**: {alt['why_rejected']}\n"

        md += "\n## 💡 Key Insights\n"
        for insight in self.key_insights:
            md += f"- {insight}\n"

        md += "\n## 🏗️ Architecture Summary\n"
        md += f"{self.architecture_summary}\n"

        return md
