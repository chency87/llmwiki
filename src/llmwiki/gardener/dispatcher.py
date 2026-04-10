from typing import Dict, Optional
from pydantic_ai.models import Model
from llmwiki.agents.base import BaseAgent
from llmwiki.agents.personas import (
    TRIAGE_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    GARDENER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    COMPOUNDER_SYSTEM_PROMPT
)

class Dispatcher:
    def __init__(
        self,
        provider: str = "openai",
        model_name: str = "gpt-4o",
        base_url: str = None,
        api_key: str = None,
        model: Optional[Model] = None,
        vault_path: str = "vault"
    ):
        self.vault_path = vault_path
        self.config = {
            "provider": provider,
            "model_name": model_name,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "vault_path": vault_path
        }
        self.agents = self._init_agents()

    def _init_agents(self) -> Dict[str, BaseAgent]:
        return {
            "triage": BaseAgent("Triage", TRIAGE_SYSTEM_PROMPT, **self.config),
            "planner": BaseAgent("Planner", PLANNER_SYSTEM_PROMPT, **self.config),
            "gardener": BaseAgent("Gardener", GARDENER_SYSTEM_PROMPT, **self.config),
            "reviewer": BaseAgent("Reviewer", REVIEWER_SYSTEM_PROMPT, **self.config),
            "compounder": BaseAgent("Compounder", COMPOUNDER_SYSTEM_PROMPT, **self.config)
        }

    async def dispatch(self, user_request: str):
        # 1. Start with the Planner to decide what to do
        planner_prompt = f"User Request: {user_request}\n\nDecide which agent(s) should handle this and in what order."
        plan_result = await self.agents["planner"].run(planner_prompt)
        return plan_result.output
