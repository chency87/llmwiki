import re
from pydantic_ai.models import Model
from llmwiki.utils.resilience import retry_async
from llmwiki.agents.base import BaseAgent

class QAEngine:
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
            "You are the LLMWiki QA Librarian. Your job is to answer questions by navigating the knowledge wiki.\n\n"
            "THE CONSTITUTION:\n"
            "- You MUST follow the naming conventions, citation styles, and workflows defined in the `WIKI SCHEMA` provided in your initial context.\n\n"
            "OPTIMIZATION RULES:\n"
            "- ALWAYS check the provided INITIAL CONTEXT before calling tools.\n"
            "- Use `query_data_file` to analyze large structured datasets (CSV, Parquet) in vault/raw/ via SQL.\n"
            "- Aim to answer the question in ONE TURN if the provided context is sufficient.\n\n"
            "CLASSIFICATION:\n"
            "- When you find a definitive answer, categorize and tag it appropriately according to the schema when saving."
        )
        
        self.base = BaseAgent(
            name="qa",
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
    async def ask(self, question: str) -> str:
        # 1. Pre-fetch Index and Schema
        index_content = self.deps.vt.read_page("_index.md")
        schema_content = self.deps.vt.read_page("schema.md")
        
        # 2. Search and Pre-fetch relevant content
        initial_search = self.deps.km.search_entities_keyword(question, limit=5)
        
        related_content = []
        for ent in initial_search[:3]:
            content = self.deps.vt.read_page(ent["path"])
            related_content.append(f"--- ENTITY: {ent['name']} ({ent['path']}) ---\n{content}")
        
        context_block = (
            f"WIKI SCHEMA (The Rules):\n{schema_content}\n\n"
            f"WIKI INDEX:\n{index_content}\n\n"
            f"PRE-FETCHED RELATED ENTITY CONTENT:\n" + "\n\n".join(related_content) + "\n\n"
            f"OTHER POTENTIAL ENTITIES (Summaries only):\n{initial_search[3:]}"
        )
        
        prompt = (
            f"Question: {question}\n\n"
            f"INITIAL CONTEXT:\n{context_block}\n\n"
            "Answer this question using the context provided. "
            "If the answer is found in the INITIAL CONTEXT, provide it IMMEDIATELY without further tool calls. "
            "Only use tools if the provided context is insufficient."
        )
        
        result = await self.base.run(prompt)
        answer = result.output
        
        # Save to qa/
        slug = re.sub(r'[^a-z0-9]+', '-', question.lower()).strip('-')
        qa_content = f"# Q: {question}\n\n{answer}\n"
        self.deps.vt.write_page(f"qa/{slug}", qa_content)
        
        return answer
