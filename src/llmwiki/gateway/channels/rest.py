import uvicorn
from typing import Any, Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from ..base import BaseChannel

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = "rest-user"
    user_id: Optional[str] = None

class RestChannel(BaseChannel):
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, api_key: str = None):
        super().__init__("rest")
        self.host = host
        self.port = port
        self.api_key = api_key
        self.app = FastAPI(title="LLMWiki REST Gateway")
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/api/chat")
        async def chat(
            request: ChatRequest, 
            x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        ):
            # Auth check
            if self.api_key and x_api_key != self.api_key:
                raise HTTPException(status_code=401, detail="Invalid API Key")
            
            # Use the manager injected during start()
            if not hasattr(self, "_manager"):
                raise HTTPException(status_code=503, detail="Gateway not ready")
            
            response = await self._manager.handle_message(
                self.name, 
                request.chat_id, 
                request.message, 
                user_id=request.user_id
            )
            return {"response": response}

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

    async def start(self, manager: Any):
        self._manager = manager
        manager.logger.log("GATEWAY", "INFO", f"Starting REST listener on {self.host}:{self.port}...")
        
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        
        # Run uvicorn in the background or as a task
        # Since GatewayManager.start() gathers these, we can just await it
        await server.serve()

    async def send_message(self, chat_id: str, text: str):
        # REST is synchronous for the request/response cycle, 
        # so send_message isn't used for the immediate response.
        pass
