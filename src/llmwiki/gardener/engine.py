from typing import Optional
from pydantic_ai.models import Model
from llmwiki.utils.logger import get_logger
from llmwiki.utils.resilience import retry_async
from llmwiki.agents.base import BaseAgent

class Gardener:
    def __init__(
        self, 
        provider: str = "openai",
        model_name: str = "gpt-4o", 
        model: Model = None,
        base_url: str = None,
        api_key: str = None,
        vault_path: str = "vault"
    ):
        self.provider = provider
        system_prompt = (
            "You are the LLMWiki Gardener. You perform COMPILATION. Your goal is to synthesize new "
            "information into a persistent, interlinked Markdown wiki.\n\n"
            "THE CONSTITUTION:\n"
            "- You MUST follow the structure, naming conventions, and workflows defined in the `WIKI SCHEMA` provided in your initial context.\n\n"
            "CORE PRINCIPLES:\n"
            "- WIKI AS MEMORY: Navigate by reading `_index.md` and following `[[Wiki Links]]`.\n"
            "- COMPILATION: Update ALL relevant entity pages. Do not just create a summary.\n"
            "- BIDIRECTIONAL LINKS: Every page should link to its neighbors.\n"
            "- CLASSIFICATION: When calling `write_page`, always provide relevant `categories` and `tags` as defined in the schema."
        )
        
        # Use BaseAgent to handle all tool registration centrally
        self.base = BaseAgent(
            name="gardener",
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
    async def process_new_source(self, filename: str, extracted_text: Optional[str] = None, file_path: Optional[str] = None):
        self.logger.log("GARDEN", "INFO", f"Starting ultra-optimized synthesis for: {filename}")

        # 1. Pre-fetch Index and Schema
        index_content = self.deps.vt.read_page("_index.md")
        schema_content = self.deps.vt.read_page("schema.md")

        # 2. Identify and Pre-fetch top related entities
        import re
        search_query = re.sub(r'[^a-zA-Z0-9 ]', ' ', filename)
        initial_search = self.deps.km.search_entities_keyword(search_query, limit=5)

        related_content = []
        # Pre-read the top 3 existing entities
        for ent in initial_search[:3]:
            content = self.deps.vt.read_page(ent["path"])
            related_content.append(f"--- ENTITY: {ent['name']} ({ent['path']}) ---\n{content}")

        context_block = (
            f"WIKI SCHEMA (The Rules):\n{schema_content}\n\n"
            f"WIKI INDEX:\n{index_content}\n\n"
            f"PRE-FETCHED RELATED ENTITY CONTENT:\n" + "\n\n".join(related_content) + "\n\n"
            f"OTHER POTENTIAL ENTITIES (Summaries only):\n{initial_search[3:]}"
        )

        
        if self.provider.endswith("-cli") and file_path:
            prompt = (
                f"New source: {filename}\nLocation: {file_path}\n\n"
                f"INITIAL CONTEXT:\n{context_block}\n\n"
                "Please read the file using your tools and compile its information into the wiki. "
                "I have pre-fetched the content of the most relevant existing pages above to save you time. "
                "Use the provided context instead of calling `read_page` where possible."
            )
        else:
            content_display = f"Content:\n{extracted_text}" if extracted_text else "Content unavailable."
            prompt = (
                f"New source: {filename}\n\n{content_display}\n\n"
                f"INITIAL CONTEXT:\n{context_block}\n\n"
                "Process this into the wiki. Use the pre-fetched context above to identify and update existing entities in one turn."
            )

        try:
            await self.base.run(prompt)
            self.deps.vt.append_log(f"Synthesized {filename} into the wiki.")
            self.logger.log("GARDEN", "INFO", f"Finished optimized synthesis for: {filename}")
        except Exception as e:
            self.logger.log("GARDEN", "ERROR", f"Synthesis failed for {filename}: {str(e)}")
            raise e
