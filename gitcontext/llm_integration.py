"""LLM integration for context analysis"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from .models import OTALog, ContextCommit, SquashResult


class LLMAnalyzer:
    """Analyzes context using various LLM providers"""

    def __init__(self, provider: str = "openai", model: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.api_key = api_key or self._get_api_key(provider)

    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        models = {
            "openai": "gpt-4-turbo-preview",
            "anthropic": "claude-3-opus-20240229",
            "ollama": "llama3",
            "deepseek": "deepseek-chat",
            "mock": "mock-model"  # For testing without API
        }
        return models.get(provider, "gpt-4-turbo-preview")

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from environment"""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }
        return os.getenv(env_vars.get(provider, ""))

    def analyze_ota_logs(self, logs: List[OTALog]) -> Dict[str, Any]:
        """Analyze OTA logs to extract decisions and insights"""
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

        response = self._call_llm(prompt)
        try:
            # Try to parse JSON from response
            # Find JSON block if it exists
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            result = json.loads(response.strip())
            return {
                "decisions": result.get("decisions", []),
                "alternatives": result.get("alternatives", []),
                "insights": result.get("insights", [])
            }
        except:
            # Fallback: return empty but log warning
            print(f"Warning: Failed to parse LLM response: {response[:100]}...")
            return {"decisions": [], "alternatives": [], "insights": []}

    def squash_branch_history(self, branch_name: str, commits: List[ContextCommit],
                              current_context: Optional[Dict] = None) -> SquashResult:
        """Analyze entire branch history and create squashed summary"""

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
            all_alternatives.extend(commit.alternatives)
            all_ota_logs.extend(commit.ota_logs)
            commit_messages.append(f"- {commit.timestamp.strftime('%Y-%m-%d %H:%M')}: {commit.message}")

        # Create prompt for LLM
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

        response = self._call_llm(prompt)

        try:
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return SquashResult(
                decisions=data.get("decisions", []),
                rejected_alternatives=data.get("rejected_alternatives", []),
                key_insights=data.get("key_insights", []),
                architecture_summary=data.get("architecture_summary", "No summary available"),
                ota_count=len(all_ota_logs),
                original_commits=len(commits),
                branch_name=branch_name
            )
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Fallback: create simple summary
            return SquashResult(
                decisions=all_decisions[-5:] if all_decisions else [],  # Last 5 decisions
                rejected_alternatives=all_alternatives[-3:] if all_alternatives else [],
                key_insights=["Analysis failed, using fallback summary"],
                architecture_summary=f"Branch had {len(commits)} commits with {len(all_decisions)} decisions",
                ota_count=len(all_ota_logs),
                original_commits=len(commits),
                branch_name=branch_name
            )

    def _call_llm(self, prompt: str) -> str:
        """Call appropriate LLM based on provider"""
        if self.provider == "mock":
            return self._mock_call(prompt)
        elif self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.provider == "ollama":
            return self._call_ollama(prompt)
        elif self.provider == "deepseek":
            return self._call_deepseek(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _mock_call(self, prompt: str) -> str:
        """Mock LLM for testing"""
        # Generate consistent mock response based on prompt hash
        hash_val = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)

        if "squash_branch" in prompt or "SQUASHED summary" in prompt:
            return json.dumps({
                "decisions": [
                    "Use JWT for authentication",
                    "Implement Redis caching for sessions",
                    "Use PostgreSQL for main database"
                ],
                "rejected_alternatives": [
                    {"what": "Session-based auth", "why_rejected": "Scalability issues"},
                    {"what": "MongoDB", "why_rejected": "Need ACID transactions"}
                ],
                "key_insights": [
                    "JWT works better with microservices",
                    "Redis TTL should be 15 minutes for security"
                ],
                "architecture_summary": "Built a scalable authentication service using JWT tokens stored in Redis cache with PostgreSQL as primary database."
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "decisions": ["Implemented error handling", "Added logging"],
                "alternatives": [],
                "insights": ["Always validate input"]
            }, ensure_ascii=False)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        import openai
        openai.api_key = self.api_key

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a precise code and architecture analyst. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._mock_call(prompt)  # Fallback to mock

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system="You are a precise code and architecture analyst. Always return valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return self._mock_call(prompt)

    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama instance"""
        import requests

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"System: You are a precise code and architecture analyst. Always return valid JSON.\n\nUser: {prompt}",
                    "stream": False,
                    "temperature": 0.3
                }
            )
            return response.json()["response"]
        except Exception as e:
            print(f"Ollama error: {e}")
            return self._mock_call(prompt)

    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API"""
        import requests

        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system",
                         "content": "You are a precise code and architecture analyst. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"DeepSeek API error: {e}")
            return self._mock_call(prompt)
