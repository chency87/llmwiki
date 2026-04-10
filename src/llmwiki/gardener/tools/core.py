from typing import Dict, Any, List
from llmwiki.db.store import Store
from duckduckgo_search import DDGS

class KnowledgeMap:
    def __init__(self, vault_path: str = "vault"):
        self.store = Store(vault_path)

    def get_map(self) -> Dict[str, Any]:
        return self.store.get_knowledge_map()

    def update_entity(self, name: str, path: str, summary: str, categories: str = "", tags: str = ""):
        self.store.update_entity(name, path, summary, categories=categories, tags=tags)

class WebSearch:
    @staticmethod
    def search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                return [
                    {"title": r["title"], "href": r["href"], "body": r["body"]}
                    for r in results
                ]
        except Exception as e:
            return [{"error": str(e)}]
