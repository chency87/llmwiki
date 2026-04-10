from pydantic_ai.models import Model
from llmwiki.utils.resilience import retry_async
from llmwiki.utils.logger import get_logger
from llmwiki.agents.base import BaseAgent

class Evolver:
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
            "You are the LLMWiki Evolution Engine. Your job is to improve the quality and structure of the knowledge codebase.\n\n"
            "TASKS:\n"
            "1. DEDUPLICATION: Identify entity pages that cover the same topic and should be merged.\n"
            "2. LINK STRENGTHENING: Suggest new [[Wiki Links]] between entities that are conceptually related.\n"
            "3. SUMMARY OPTIMIZATION: Improve the summaries in the Knowledge Map to be more useful for the Gardener.\n"
            "4. ORPHAN CLEANUP: Find pages that have no incoming or outgoing links and suggest connections.\n\n"
            "OPTIMIZATION RULES:\n"
            "- ALWAYS consult the Knowledge Map before reading pages.\n"
            "- Use `read_pages_batch` to analyze multiple candidates for merging or linking in one turn."
        )
        
        self.base = BaseAgent(
            name="evolver",
            system_prompt=system_prompt,
            provider=provider,
            model_name=model_name,
            model=model,
            base_url=base_url,
            api_key=api_key,
            vault_path=vault_path
        )
        self.deps = self.base.deps
        self.logger = get_logger(vault_path)

    @retry_async(max_attempts=3)
    async def evolve(self):
        self.logger.log("EVOLVE", "INFO", "Starting autonomous evolution cycle.")
        prompt = (
            "Scan the entire Knowledge Map. Look for redundant entities or missing connections. "
            "Perform at least three 'Evolution' actions: merging duplicates, adding missing links, or improving summaries. "
            "Report exactly what you changed."
        )
        try:
            result = await self.base.run(prompt)
            self.logger.log("EVOLVE", "INFO", "Evolution cycle complete.")
            return result.output
        except Exception as e:
            self.logger.log("EVOLVE", "ERROR", f"Evolution failed: {e}")
            raise e
