"""Ollama local provider implementation."""

import requests
import json
from typing import List, Dict, Any, Optional

from .provider import LLMProvider
from ..models.ota import OTALog
from ..models.types import ContextCommit, SquashResult, Alternative
from ..utils.logger import Logger


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, model: Optional[str] = None, base_url: str = "http://localhost:11434"):
        super().__init__(model or "llama3", None)
        self.base_url = base_url.rstrip('/')

    def analyze_ota_logs(self, logs: List[OTALog]) -> Dict[str, Any]:
        """Analyze OTA logs using local model."""
        if not logs:
            return {"decisions": [], "alternatives": [], "insights": []}

        log_text = "\n---\n".join([
            f"Timestamp: {log.timestamp}\n"
            f"Thought: {log.thought}\n"
            f"Action: {log.action}\n"
            f"Result: {log.result}\n"
            f"Files: {', '.join(log.files_affected)}"
            for log in logs[-10:]  # Take fewer for smaller models
        ])

        prompt = f"""You are analyzing AI development logs. Extract key information.

Logs:
{log_text}

Extract and return as JSON:
1. "decisions": list of key decisions made (what was decided)
2. "alternatives": list of {{"what": "...", "why_rejected": "..."}} for alternatives considered but rejected
3. "insights": list of important learnings or realizations

Return ONLY valid JSON, no other text."""

        response = self._call(prompt)
        result = self._parse_json_response(response)

        return {
            "decisions": result.get("decisions", []),
            "alternatives": result.get("alternatives", []),
            "insights": result.get("insights", [])
        }

    def squash_branch_history(
            self,
            branch_name: str,
            commits: List[ContextCommit],
            current_context: Optional[Dict] = None
    ) -> SquashResult:
        """Squash branch history using local model."""
        if not commits:
            return SquashResult(
                decisions=[],
                rejected_alternatives=[],
                key_insights=[],
                architecture_summary="No commits in branch",
                ota_count=0,
                original_commits=0,
                branch_name=branch_name
            )

        # Summarize for smaller context window
        all_decisions = []
        for commit in commits[-5:]:  # Take last 5 commits
            all_decisions.extend(commit.decisions[-3:])  # Take last 3 decisions each

        commit_messages = [
            f"- {commit.timestamp.strftime('%Y-%m-%d')}: {commit.message[:50]}"
            for commit in commits[-5:]
        ]

        prompt = f"""Analyze development history of branch '{branch_name}'.

Recent commits:
{chr(10).join(commit_messages)}

Key decisions made:
{json.dumps(all_decisions, indent=2, ensure_ascii=False)[:500]}

Create a summary with:
1. "decisions": list of final decisions (max 5)
2. "key_insights": list of learnings (max 3)
3. "architecture_summary": one sentence summary

Return as JSON."""

        response = self._call(prompt)
        data = self._parse_json_response(response)

        return SquashResult(
            decisions=data.get("decisions", [])[:5],
            rejected_alternatives=[],  # Smaller models struggle with alternatives
            key_insights=data.get("key_insights", [])[:3],
            architecture_summary=data.get("architecture_summary", ""),
            ota_count=0,  # Don't try to count
            original_commits=len(commits),
            branch_name=branch_name
        )

    def generate_commit_message(self, changes: List[str], context: Optional[str] = None) -> str:
        """Generate a commit message."""
        changes_text = "\n".join(f"- {change}" for change in changes[:5])

        prompt = f"""Generate a short git commit message:

Changes:
{changes_text}

Return only the commit message, one line."""

        return self._call(prompt).strip()

    def _call(self, prompt: str, system: Optional[str] = None) -> str:
        """Call Ollama API."""
        try:
            full_prompt = prompt
            if system:
                full_prompt = f"System: {system}\n\nUser: {prompt}"

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
            )
            return response.json()["response"]
        except Exception as e:
            Logger.error(f"Ollama error: {e}")
            raise
