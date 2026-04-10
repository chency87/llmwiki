from pydantic_ai.models import Model
from llmwiki.utils.resilience import retry_async
from llmwiki.agents.base import BaseAgent

class Maintainer:
    def __init__(
        self, 
        provider: str = "openai",
        model_name: str = "gpt-4o", 
        base_url: str = None,
        api_key: str = None,
        model: Model = None,
        vault_path: str = "vault"
    ):
        system_prompt = (
            "You are the LLMWiki Auditor. Your job is to ensure the integrity, consistency, and accuracy of the knowledge codebase.\n\n"
            "TASKS:\n"
            "1. CONTRADICTION DETECTION: Find statements in different pages that conflict with each other.\n"
            "2. BROKEN LINK CHECK: Identify `[[Wiki Links]]` that point to non-existent pages.\n"
            "3. ACCURACY AUDIT: Verify that claims in the wiki are correctly attributed to their source summaries.\n"
            "4. QUALITY CONTROL: Suggest improvements for clarity, formatting, and naming conventions."
        )
        
        self.base = BaseAgent(
            name="maintainer",
            system_prompt=system_prompt,
            provider=provider,
            model_name=model_name,
            model=model,
            base_url=base_url,
            api_key=api_key,
            vault_path=vault_path
        )
        self.deps = self.base.deps

    @retry_async(max_attempts=3)
    async def maintain(self):
        prompt = (
            "Perform a comprehensive audit of the knowledge vault. Identify any contradictions, broken links, or quality issues. "
            "Return a structured report of your findings."
        )
        result = await self.base.run(prompt)
        return result.output
