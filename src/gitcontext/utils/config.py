"""Configuration management for GitContext."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file
load_dotenv()


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2000

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Create config from environment variables."""
        return cls(
            provider=os.getenv("GITCONTEXT_LLM_PROVIDER", "openai"),
            model=os.getenv("GITCONTEXT_LLM_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        )


@dataclass
class StorageConfig:
    """Storage configuration."""
    context_dir: str = ".gitcontext"
    max_history: int = 1000
    compress_archive: bool = True

    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create config from environment variables."""
        return cls(
            context_dir=os.getenv("GITCONTEXT_DIR", ".gitcontext"),
        )


@dataclass
class GitConfig:
    """Git integration configuration."""
    auto_commit: bool = False
    auto_push: bool = False
    remote_name: str = "origin"

    @classmethod
    def from_env(cls) -> 'GitConfig':
        """Create config from environment variables."""
        return cls(
            auto_commit=os.getenv("GITCONTEXT_AUTO_COMMIT", "false").lower() == "true",
            auto_push=os.getenv("GITCONTEXT_AUTO_PUSH", "false").lower() == "true",
        )


@dataclass
class Config:
    """Main configuration for GitContext."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    git: GitConfig = field(default_factory=GitConfig)
    verbose: bool = False
    debug: bool = False

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'Config':
        """Load configuration from file and environment."""
        config = cls()

        # Load from file if exists
        if path and path.exists():
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}

                # Update LLM config
                if 'llm' in data:
                    for key, value in data['llm'].items():
                        if hasattr(config.llm, key):
                            setattr(config.llm, key, value)

                # Update storage config
                if 'storage' in data:
                    for key, value in data['storage'].items():
                        if hasattr(config.storage, key):
                            setattr(config.storage, key, value)

                # Update git config
                if 'git' in data:
                    for key, value in data['git'].items():
                        if hasattr(config.git, key):
                            setattr(config.git, key, value)

                # Update main config
                config.verbose = data.get('verbose', False)
                config.debug = data.get('debug', False)

        # Override with environment variables
        env_llm = LLMConfig.from_env()
        for key in ['provider', 'model', 'api_key']:
            if getattr(env_llm, key):
                setattr(config.llm, key, getattr(env_llm, key))

        env_storage = StorageConfig.from_env()
        for key in ['context_dir']:
            if getattr(env_storage, key):
                setattr(config.storage, key, getattr(env_storage, key))

        env_git = GitConfig.from_env()
        for key in ['auto_commit', 'auto_push']:
            if getattr(env_git, key):
                setattr(config.git, key, getattr(env_git, key))

        return config

    def save(self, path: Path):
        """Save configuration to file."""
        data = {
            'llm': {
                'provider': self.llm.provider,
                'model': self.llm.model,
                'temperature': self.llm.temperature,
                'max_tokens': self.llm.max_tokens,
            },
            'storage': {
                'context_dir': self.storage.context_dir,
                'max_history': self.storage.max_history,
                'compress_archive': self.storage.compress_archive,
            },
            'git': {
                'auto_commit': self.git.auto_commit,
                'auto_push': self.git.auto_push,
                'remote_name': self.git.remote_name,
            },
            'verbose': self.verbose,
            'debug': self.debug,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
