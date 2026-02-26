"""Serialization utilities for GitContext."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import gzip
import shutil


class Serializer:
    """Handles serialization/deserialization of GitContext data."""

    @staticmethod
    def to_json(data: Any, path: Path, compress: bool = False) -> None:
        """Write data to JSON file."""
        if compress:
            path = path.with_suffix('.json.gz')
            with gzip.open(path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(path: Path, compressed: bool = False) -> Any:
        """Read data from JSON file."""
        if compressed or path.suffix == '.gz':
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

    @staticmethod
    def to_yaml(data: Any, path: Path) -> None:
        """Write data to YAML file."""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def from_yaml(path: Path) -> Any:
        """Read data from YAML file."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def to_markdown(text: str, path: Path) -> None:
        """Write text to markdown file."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

    @staticmethod
    def compress_file(path: Path) -> Path:
        """Compress a file with gzip."""
        gz_path = path.with_suffix(path.suffix + '.gz')
        with open(path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return gz_path

    @staticmethod
    def decompress_file(path: Path) -> Path:
        """Decompress a gzip file."""
        if path.suffix != '.gz':
            return path

        out_path = path.with_suffix('')
        with gzip.open(path, 'rb') as f_in:
            with open(out_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return out_path