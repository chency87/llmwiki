from .manager import CapabilitiesManager
from .native import (
    read_page, 
    read_pages_batch, 
    write_page, 
    search_vault, 
    search_entities, 
    get_backlinks, 
    get_knowledge_map, 
    append_log
)
from .data import query_data_file

def get_default_capabilities(config) -> CapabilitiesManager:
    """Creates a manager with all core LLMWiki tools registered."""
    mgr = CapabilitiesManager(config)
    mgr.register_native_tool("read_page", read_page)
    mgr.register_native_tool("read_pages_batch", read_pages_batch)
    mgr.register_native_tool("write_page", write_page)
    mgr.register_native_tool("search_vault", search_vault)
    mgr.register_native_tool("search_entities", search_entities)
    mgr.register_native_tool("get_backlinks", get_backlinks)
    mgr.register_native_tool("get_knowledge_map", get_knowledge_map)
    mgr.register_native_tool("append_log", append_log)
    mgr.register_native_tool("query_data_file", query_data_file)
    return mgr
