"""LLM provider factory."""

from typing import Optional

from .provider import LLMProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider
from .deepseek import DeepSeekProvider
from ..utils.logger import Logger
from ..utils.errors import LLMError


class MockProvider(LLMProvider):
    """Mock provider for testing."""

    def analyze_ota_logs(self, logs, **kwargs):
        return {
            "decisions": ["Use JWT for auth", "Implement Redis cache"],
            "alternatives": [
                {"what": "Session auth", "why_rejected": "Scalability issues"}
            ],
            "insights": ["JWT works well with microservices"]
        }

    def squash_branch_history(self, branch_name, commits, current_context=None):
        from ..models.types import SquashResult
        return SquashResult(
            decisions=["Use JWT", "Redis cache"],
            rejected_alternatives=[],
            key_insights=["Keep it simple"],
            architecture_summary="Built auth service",
            ota_count=0,
            original_commits=len(commits),
            branch_name=branch_name
        )

    def generate_commit_message(self, changes, context=None):
        return "Update authentication"

    def _call(self, prompt, system=None):
        return "{}"


def create_provider(
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None
) -> LLMProvider:
    """Create LLM provider instance."""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "deepseek": DeepSeekProvider,
        "mock": MockProvider,
    }

    if provider not in providers:
        raise LLMError(f"Unknown provider: {provider}")

    Logger.info(f"Creating {provider} provider with model {model or 'default'}")

    if provider == "ollama":
        return providers[provider](model)
    else:
        return providers[provider](model, api_key)
