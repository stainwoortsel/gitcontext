"""Utility functions"""
import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict

def ensure_dir(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file"""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Save YAML file"""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path: Path, data: Dict[str, Any]) -> None:
    """Save JSON file"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_timestamp() -> str:
    """Get current timestamp string"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
