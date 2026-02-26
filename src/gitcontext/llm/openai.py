"""OpenAI provider implementation."""

import openai
from typing import List, Dict, Any, Optional
import json

from .provider import LLMProvider
from ..models.ota import OTALog
from ..models.types import ContextCommit, SquashResult, Alternative
from ..utils.logger import Logger


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(model or "gpt-4-turbo-preview", api_key)
        openai.api_key = self.api_key

    def analyze_ota_logs(self, logs: List[OTALog]) -> Dict[str, Any]:
        """Analyze OTA logs using OpenAI."""
        if not logs:
            return {"decisions": [], "alternatives": [], "insights": []}

        # Format logs for prompt
        log_text = "\n---\n".join([
            f"Timestamp: {log.timestamp}\n"
            f"Thought: {log.thought}\n"
            f"Action: {log.action}\n"
            f"Result: {log.result}\n"
            f"Files: {', '.join(log.files_affected)}"
            for log in logs[-15:]  # Take last 15 for context
        ])

        prompt = f"""You are analyzing AI development logs. Extract key information.

Logs:
{log_text}

Extract and return as JSON:
1. "decisions": list of key decisions made (what was decided)
2. "alternatives": list of {{"what": "...", "why_rejected": "..."}} for alternatives considered but rejected
3. "insights": list of important learnings or realizations

Return ONLY valid JSON, no other text.
"""

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
        """Squash branch history using OpenAI."""
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

        # Collect all data
        all_decisions = []
        all_alternatives = []
        all_ota_logs = []
        commit_messages = []

        for commit in commits:
            all_decisions.extend(commit.decisions)
            all_alternatives.extend([a.to_dict() for a in commit.alternatives])
            all_ota_logs.extend([log.to_dict() for log in commit.ota_logs])
            commit_messages.append(
                f"- {commit.timestamp.strftime('%Y-%m-%d %H:%M')}: {commit.message}"
            )

        prompt = f"""You are analyzing the complete development history of branch '{branch_name}'.

COMMITS ({len(commits)}):
{chr(10).join(commit_messages)}

DECISIONS MADE:
{json.dumps(all_decisions, indent=2, ensure_ascii=False)}

ALTERNATIVES CONSIDERED:
{json.dumps(all_alternatives, indent=2, ensure_ascii=False)}

OTA LOGS COUNT: {len(all_ota_logs)}

CURRENT CONTEXT:
{json.dumps(current_context, indent=2, ensure_ascii=False)[:1000] if current_context else "None"}

Create a SQUASHED summary that captures the essence of this development. Focus on the FINAL OUTCOME.

Return as JSON with:
1. "decisions": list of FINAL architectural decisions that were actually implemented (deduplicate, remove experiments)
2. "rejected_alternatives": list of {{"what": "...", "why_rejected": "..."}} for seriously considered alternatives
3. "key_insights": list of important learnings (max 5)
4. "architecture_summary": string describing what was actually built (2-3 sentences)

Return ONLY valid JSON.
"""

        response = self._call(prompt)
        data = self._parse_json_response(response)

        # Convert alternatives to Alternative objects
        alternatives = [
            Alternative(**alt) if isinstance(alt, dict) else alt
            for alt in data.get("rejected_alternatives", [])
        ]

        return SquashResult(
            decisions=data.get("decisions", []),
            rejected_alternatives=alternatives,
            key_insights=data.get("key_insights", []),
            architecture_summary=data.get("architecture_summary", ""),
            ota_count=len(all_ota_logs),
            original_commits=len(commits),
            branch_name=branch_name
        )

    def generate_commit_message(self, changes: List[str], context: Optional[str] = None) -> str:
        """Generate a commit message based on changes."""
        changes_text = "\n".join(f"- {change}" for change in changes)

        prompt = f"""Generate a concise git commit message based on these changes:

Changes:
{changes_text}

{f"Context: {context}" if context else ""}

The commit message should:
- Be under 50 characters for the first line
- Use imperative mood (e.g., "Add feature" not "Added feature")
- Be descriptive but concise

Return ONLY the commit message, no other text.
"""

        return self._call(prompt).strip()

    def _call(self, prompt: str, system: Optional[str] = None) -> str:
        """Call OpenAI API."""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})

            messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )

            return response.choices[0].message.content
        except Exception as e:
            Logger.error(f"OpenAI API error: {e}")
            raise
