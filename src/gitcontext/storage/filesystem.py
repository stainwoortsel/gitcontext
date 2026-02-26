"""Filesystem operations for GitContext."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import shutil
from datetime import datetime
import hashlib

from ..utils.logger import Logger
from ..utils.errors import StorageError
from .serialization import Serializer


class FileSystemStorage:
    """Handles all filesystem operations for GitContext."""

    def __init__(self, root_path: Union[str, Path], context_dir: str = ".gitcontext"):
        self.root_path = Path(root_path).absolute()
        self.context_path = self.root_path / context_dir
        self.serializer = Serializer()

    def ensure_dir(self, *parts: str) -> Path:
        """Ensure directory exists and return its path."""
        path = self.context_path.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_path(self, *parts: str) -> Path:
        """Get path relative to context directory."""
        return self.context_path.joinpath(*parts)

    def exists(self, *parts: str) -> bool:
        """Check if path exists."""
        return self.get_path(*parts).exists()

    def list_dir(self, *parts: str) -> List[Path]:
        """List contents of directory."""
        path = self.get_path(*parts)
        if not path.exists():
            return []
        return list(path.iterdir())

    def save_json(self, data: Any, *parts: str, compress: bool = False) -> Path:
        """Save data as JSON."""
        path = self.get_path(*parts)
        self.ensure_dir(*parts[:-1])
        self.serializer.to_json(data, path, compress)
        return path

    def load_json(self, *parts: str, compressed: bool = False) -> Any:
        """Load data from JSON."""
        path = self.get_path(*parts)
        if not path.exists():
            raise StorageError(f"File not found: {path}")
        return self.serializer.from_json(path, compressed)

    def save_yaml(self, data: Any, *parts: str) -> Path:
        """Save data as YAML."""
        path = self.get_path(*parts)
        self.ensure_dir(*parts[:-1])
        self.serializer.to_yaml(data, path)
        return path

    def load_yaml(self, *parts: str) -> Any:
        """Load data from YAML."""
        path = self.get_path(*parts)
        if not path.exists():
            raise StorageError(f"File not found: {path}")
        return self.serializer.from_yaml(path)

    def save_text(self, text: str, *parts: str) -> Path:
        """Save text file."""
        path = self.get_path(*parts)
        self.ensure_dir(*parts[:-1])
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return path

    def load_text(self, *parts: str) -> str:
        """Load text file."""
        path = self.get_path(*parts)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def delete(self, *parts: str) -> bool:
        """Delete file or directory."""
        path = self.get_path(*parts)
        if not path.exists():
            return False

        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
        return True

    def copy(self, src: List[str], dst: List[str]) -> None:
        """Copy file or directory."""
        src_path = self.get_path(*src)
        dst_path = self.get_path(*dst)

        self.ensure_dir(*dst[:-1])

        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
        else:
            shutil.copytree(src_path, dst_path)

    def move(self, src: List[str], dst: List[str]) -> None:
        """Move file or directory."""
        src_path = self.get_path(*src)
        dst_path = self.get_path(*dst)

        self.ensure_dir(*dst[:-1])
        shutil.move(str(src_path), str(dst_path))

    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Get SHA256 hash of file content."""
        if isinstance(file_path, str):
            file_path = self.root_path / file_path

        if not file_path.exists():
            return ""

        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def get_files_snapshot(self, tracked_files: List[str]) -> Dict[str, str]:
        """Get snapshot of current files (path -> hash)."""
        snapshot = {}
        for file in tracked_files:
            file_path = self.root_path / file
            if file_path.exists():
                snapshot[file] = self.get_file_hash(file_path)
        return snapshot

    def create_temp_file(self, data: Any, suffix: str = '.json') -> Path:
        """Create a temporary file."""
        temp_dir = self.ensure_dir('temp')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        path = temp_dir / f"temp_{timestamp}{suffix}"

        if suffix == '.json':
            self.serializer.to_json(data, path)
        elif suffix == '.yaml':
            self.serializer.to_yaml(data, path)
        else:
            with open(path, 'w') as f:
                f.write(str(data))

        return path

    def cleanup_temp(self, max_age_hours: int = 24) -> int:
        """Clean up old temporary files."""
        temp_dir = self.get_path('temp')
        if not temp_dir.exists():
            return 0

        count = 0
        now = datetime.now()

        for path in temp_dir.iterdir():
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                age = (now - mtime).total_seconds() / 3600
                if age > max_age_hours:
                    path.unlink()
                    count += 1

        return count
