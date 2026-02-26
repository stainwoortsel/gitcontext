"""OTA (Overthinking Analysis) log models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


class OTALog(BaseModel):
    """
    Represents a single OTA (Overthinking Analysis) log entry.

    This captures the AI's thought process during development, including
    what was considered, what action was taken, and what resulted.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    thought: str = Field(..., min_length=1, description="What the AI was thinking")
    action: str = Field(..., min_length=1, description="What action was taken")
    result: str = Field(..., min_length=1, description="What happened as a result")
    timestamp: datetime = Field(default_factory=datetime.now)
    files_affected: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('files_affected', pre=True)
    def validate_files(cls, v):
        """Ensure files_affected is a list."""
        if isinstance(v, str):
            return [f.strip() for f in v.split(',')]
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def summary(self) -> str:
        """Get a brief summary of the log."""
        return f"{self.thought[:50]}... → {self.result[:50]}..."

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OTALog':
        """Create from dictionary."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class OTACollection(BaseModel):
    """Collection of OTA logs with analysis."""

    logs: List[OTALog] = Field(default_factory=list)
    branch: Optional[str] = None
    commit_id: Optional[str] = None

    def add(self, log: OTALog):
        """Add a log to the collection."""
        self.logs.append(log)

    def get_recent(self, limit: int = 10) -> List[OTALog]:
        """Get most recent logs."""
        return sorted(
            self.logs,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'logs': [log.to_dict() for log in self.logs],
            'branch': self.branch,
            'commit_id': self.commit_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OTACollection':
        """Create from dictionary."""
        logs = [OTALog.from_dict(log) for log in data.get('logs', [])]
        return cls(
            logs=logs,
            branch=data.get('branch'),
            commit_id=data.get('commit_id'),
        )
