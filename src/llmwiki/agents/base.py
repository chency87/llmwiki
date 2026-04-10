from typing import Optional, List
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from llmwiki.gardener.tools import VaultTools
from llmwiki.db.store import Store
from .cli_model import GeminiCLIModel, CodexCLIModel
from .capabilities import CapabilitiesManager, get_default_capabilities

class CrewDeps:
    def __init__(self, vault_path: str = "vault"):
        self.vt = VaultTools(vault_path)
        self.km = Store(vault_path)

class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        provider: str = "openai",
        model_name: str = "gpt-4o",
        base_url: str = None,
        api_key: str = None,
        model: Optional[Model] = None,
        vault_path: str = "vault",
        capabilities: Optional[CapabilitiesManager] = None
    ):
        self.name = name
        if not model:
            if provider == "gemini-cli":
                model = GeminiCLIModel(agent_id=name.lower(), vault_path=vault_path)
            elif provider == "codex-cli":
                model = CodexCLIModel(agent_id=name.lower(), vault_path=vault_path)
            else:
                model = OpenAIModel(model_name, base_url=base_url, api_key=api_key)
        
        self.deps = CrewDeps(vault_path)
        self.agent = Agent(
            model,
            deps_type=CrewDeps,
            system_prompt=system_prompt,
        )
        
        # Use provided capabilities or default ones
        from llmwiki.utils import settings
        self.capabilities = capabilities or get_default_capabilities(settings)
        self.capabilities.attach_to_agent(self.agent)

    async def run(self, prompt: str, message_history: Optional[List] = None):
        return await self.agent.run(prompt, deps=self.deps, message_history=message_history)
