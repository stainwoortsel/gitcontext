"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.ota import OTALog
from ..models.types import ContextCommit, SquashResult


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def analyze_ota_logs(self, logs: List[OTALog]) -> Dict[str, Any]:
        """Analyze OTA logs to extract decisions and insights."""
        pass

    @abstractmethod
    def squash_branch_history(
            self,
            branch_name: str,
            commits: List[ContextCommit],
            current_context: Optional[Dict] = None
    ) -> SquashResult:
        """Analyze branch history and create squashed summary."""
        pass

    @abstractmethod
    def generate_commit_message(self, changes: List[str], context: Optional[str] = None) -> str:
        """Generate a commit message based on changes."""
        pass

    @abstractmethod
    def _call(self, prompt: str, system: Optional[str] = None) -> str:
        """Make the actual API call."""
        pass

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        import json

        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        # Try to find JSON object
        try:
            return json.loads(response.strip())
        except:
            # Try to find anything that looks like JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

            # Return empty dict if parsing fails
            return {}
