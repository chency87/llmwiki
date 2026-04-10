from typing import List, Dict, Optional, Union
import yaml
import re
from pydantic_ai import RunContext
from llmwiki.gardener.tools import VaultTools, KnowledgeMap, WebSearch

# We define a protocol or base class for Deps that include our tools
class CommonDeps:
    vt: VaultTools
    km: KnowledgeMap
    web: WebSearch

def read_page(ctx: RunContext[CommonDeps], page_name: str) -> str:
    """Reads a Markdown file from the vault."""
    return ctx.deps.vt.read_page(page_name)

def read_pages_batch(ctx: RunContext[CommonDeps], page_names: List[str]) -> dict:
    """Reads multiple pages at once to minimize turns."""
    return ctx.deps.vt.read_pages_batch(page_names)

def write_page(
    ctx: RunContext[CommonDeps], 
    page_name: str, 
    content: str, 
    categories: List[str] = None, 
    tags: List[str] = None,
    links_meta: List[Dict[str, Union[str, float]]] = None
) -> str:
    """
    Writes or updates a Markdown file in the vault.
    Supports optional classification and granular knowledge graph weighting.
    `links_meta` example: [{"target": "entities/MLIR", "weight": 1.0, "type": "built-on"}]
    """
    # 1. Prepare Front Matter
    front_matter = {
        "title": page_name.split('/')[-1].replace('-', ' ').title(),
        "categories": categories or [],
        "tags": tags or []
    }
    
    # 2. Add front matter to content if not already present
    if not content.strip().startswith("---"):
        yaml_block = yaml.dump(front_matter, sort_keys=False)
        final_content = f"---\n{yaml_block}---\n\n{content.lstrip()}"
    else:
        final_content = content

    # 3. Write to disk
    res = ctx.deps.vt.write_page(page_name, final_content)
    
    # 4. Update Knowledge Map (Memory)
    clean_body = re.sub(r'---.*?---', '', final_content, flags=re.DOTALL).strip()
    summary = clean_body.split('\n\n')[0][:250] if '\n\n' in clean_body else clean_body[:250]
    
    cat_str = ",".join(categories) if categories else ""
    tag_str = ",".join(tags) if tags else ""
    ctx.deps.km.update_entity(page_name, page_name, summary, categories=cat_str, tags=tag_str)

    # 5. Extract and build Weighted Graph
    # If explicit meta is provided, use it. Otherwise, extract and use defaults.
    processed_targets = set()
    if links_meta:
        for meta in links_meta:
            target = meta.get("target", "").strip()
            if not target: continue
            if '/' not in target: target = f"entities/{target}"
            
            weight = float(meta.get("weight", 1.0))
            link_type = str(meta.get("type", "related"))
            
            ctx.deps.km.add_link(page_name, target, weight=weight, link_type=link_type)
            processed_targets.add(target)

    # Fallback: Extract remaining links from text with default weight
    wiki_link_regex = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    found_links = re.findall(wiki_link_regex, final_content)
    for link in found_links:
        target = link.strip()
        if '/' not in target: target = f"entities/{target}"
        
        if target not in processed_targets:
            ctx.deps.km.add_link(page_name, target, weight=0.5, link_type="mention")
    
    return res

def search_vault(ctx: RunContext[CommonDeps], query: str) -> str:
    """Generic search over the full text of the vault."""
    return ctx.deps.vt.search_vault(query)

def search_entities(ctx: RunContext[CommonDeps], query: str) -> list:
    """
    High-accuracy keyword search in the knowledge map.
    Prioritizes entities with high-weight incoming links (Authority).
    """
    base_results = ctx.deps.km.search_entities_keyword(query)
    
    # Simple authority boost: entities with high-weight backlinks get a small rank boost
    boosted_results = []
    for ent in base_results:
        backlinks = ctx.deps.km.get_backlinks(ent["name"])
        # Sum weights of incoming links
        authority = sum(bl.get("weight", 0.1) for bl in backlinks)
        ent["authority_score"] = authority
        boosted_results.append(ent)
    
    # Sort by authority score descending (while keeping keyword relevance as primary)
    return sorted(boosted_results, key=lambda x: x["authority_score"], reverse=True)

def get_backlinks(ctx: RunContext[CommonDeps], page_name: str) -> list:
    """Returns a list of pages that link to the specified page."""
    return ctx.deps.km.get_backlinks(page_name)

def get_knowledge_map(ctx: RunContext[CommonDeps]) -> dict:
    """Returns a compact index of all known entities."""
    return ctx.deps.km.get_knowledge_map()

def append_log(ctx: RunContext[CommonDeps], message: str) -> str:
    """Adds a message to the chronological log.md."""
    return ctx.deps.vt.append_log(message)

def web_search(ctx: RunContext[CommonDeps], query: str) -> list:
    """Performs a web search to fill knowledge gaps."""
    return ctx.deps.web.search(query)
