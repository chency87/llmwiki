from pydantic_ai.models import Model
from llmwiki.utils.resilience import retry_async
from llmwiki.agents.base import BaseAgent

class Reflector:
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
            "You are the LLMWiki Reflector. Your job is to perform 'Deep Thinking' over the existing knowledge base. "
            "You look for patterns, cross-cutting themes, and high-level insights that emerge from multiple documents. "
            "You save these insights as 'Mental Models' in 'vault/pages/models/'.\n\n"
            "GUIDELINES:\n"
            "- Read the Knowledge Map and key summaries to find connections.\n"
            "- Write new pages in 'models/' that synthesize information from multiple entities/summaries.\n"
            "- Use `[[Wiki Links]]` to link to the source entities and summaries.\n"
            "- Ensure every Mental Model has a clear thesis and supporting evidence from the wiki."
        )
        
        self.base = BaseAgent(
            name="reflector",
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
    async def reflect(self):
        prompt = (
            "Analyze the current knowledge base. Look for connections between entities and documents. "
            "Identify at least one high-level insight or theme and write it as a new Mental Model page in 'models/'."
        )
        await self.base.run(prompt)
