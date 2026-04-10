from pydantic_ai.models import Model
from llmwiki.utils.resilience import retry_async
from llmwiki.agents.base import BaseAgent

class Writer:
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
            "You are the LLMWiki Author. Your job is to generate high-quality artifacts, reports, and briefings based on the knowledge vault.\n\n"
            "GUIDELINES:\n"
            "- Use the Knowledge Map to find relevant entities and summaries.\n"
            "- Synthesize information into a cohesive, well-structured document.\n"
            "- Use standard Markdown formatting.\n"
            "- Citations should be prominent and accurate."
        )
        
        self.base = BaseAgent(
            name="writer",
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
    async def brew(self, topic: str):
        prompt = f"Generate a comprehensive report on the following topic based on the wiki: {topic}"
        result = await self.base.run(prompt)
        
        # Save to artifacts/
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
        path = f"artifacts/{slug}.md"
        self.deps.vt.write_page(path, result.output)
        return path
