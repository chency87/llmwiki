import os
from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from llmwiki.db.store import Store

app = FastAPI(title="LLMWiki Dashboard")

# Mount static files and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
template_dir = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=template_dir)

# Vault connection
VAULT_PATH = str(os.getenv("LLMWIKI_VAULT", "vault"))
store = Store(VAULT_PATH)

@app.get("/")
async def index(request: Request):
    # Pass request as both a keyword argument and in the context dictionary for maximum compatibility
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"vault": VAULT_PATH}
    )

@app.get("/api/stats")
async def get_stats():
    try:
        manifest_stats = store.get_manifest_stats()
        entity_count = store.get_entity_count()
        return {
            "entities": entity_count,
            "processed": manifest_stats.get("processed", 0),
            "total_sources": sum(manifest_stats.values())
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/logs")
async def get_logs(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50)):
    try:
        # Use the trace-based pagination
        traces = store.get_paginated_traces(page=page, limit=limit)
        total_traces = store.get_trace_count()
        
        return {
            "page": page,
            "limit": limit,
            "total_traces": total_traces,
            "traces": traces
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "details": traceback.format_exc(), "traces": []}

@app.get("/api/knowledge")
async def get_knowledge():
    try:
        return store.get_knowledge_map()
    except Exception as e:
        return {"error": str(e)}
