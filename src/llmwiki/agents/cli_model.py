import asyncio
import json
import tempfile
import re
from typing import List, Optional, Any, Dict
from pydantic_ai.models import Model, ModelResponse
from pydantic_ai.messages import ModelMessage, ModelRequest, TextPart
from datetime import datetime
from pathlib import Path
from llmwiki.utils.logger import get_logger
from llmwiki.utils.resilience import retry_async
from llmwiki.utils import settings

# Global orchestrator to prevent multiple CLI instances from clashing on the same session
_agent_semaphores: Dict[str, asyncio.Semaphore] = {}
_orchestrator_lock = asyncio.Lock()

async def get_agent_semaphore(agent_id: str) -> asyncio.Semaphore:
    async with _orchestrator_lock:
        if agent_id not in _agent_semaphores:
            _agent_semaphores[agent_id] = asyncio.Semaphore(1)
        return _agent_semaphores[agent_id]

def extract_json_objects(text: str) -> List[Dict]:
    """
    Robustly extracts all complete JSON objects from a string by counting braces.
    """
    objs = []
    stack = 0
    start = -1
    for i, char in enumerate(text):
        if char == '{':
            if stack == 0:
                start = i
            stack += 1
        elif char == '}':
            stack -= 1
            if stack == 0 and start != -1:
                try:
                    obj = json.loads(text[start:i+1])
                    objs.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objs

class CLIModel(Model):
    def __init__(self, agent_id: str, vault_path: str = "vault"):
        self.agent_id = agent_id
        self.vault_path = vault_path
        from llmwiki.db.store import Store
        self.store = Store(vault_path)
        self.logger = get_logger(vault_path)

    @property
    def model_name(self) -> str:
        return f"cli:{self.agent_id}"

    @property
    def system(self) -> str:
        return "cli"

    async def _stream_exec(self, cmd: List[str], input_text: Optional[str] = None) -> str:
        """
        Executes a CLI command asynchronously, handles stdin/stdout/stderr 
        concurrently, and logs the full output as a single block to preserve formatting.
        """
        sem = await get_agent_semaphore(self.agent_id)
        
        async with sem:
            self.logger.log("CLI_AGENT", "INFO", f"[{self.agent_id}] Running: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_text else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout_chunks = []
            stderr_chunks = []
            
            async def read_stdout(stream):
                while True:
                    line = await stream.readline()
                    if not line: break
                    text = line.decode('utf-8', errors='replace')
                    stdout_chunks.append(text)

            async def read_stderr(stream):
                while True:
                    line = await stream.readline()
                    if not line: break
                    text = line.decode('utf-8', errors='replace')
                    stderr_chunks.append(text)

            async def write_stdin(stdin, text):
                try:
                    if text:
                        stdin.write(text.encode())
                        await stdin.drain()
                    if stdin.can_write_eof():
                        stdin.write_eof()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            # Run I/O operations concurrently
            tasks = [
                read_stdout(process.stdout),
                read_stderr(process.stderr)
            ]
            if input_text:
                tasks.append(write_stdin(process.stdin, input_text))
            
            await asyncio.gather(*tasks)
            await process.wait()
            
            full_stdout = "".join(stdout_chunks)
            full_stderr = "".join(stderr_chunks)

            # Log formatted STDOUT/STDERR
            if full_stdout.strip():
                self.logger.log("CLI_AGENT", "INFO", f"[{self.agent_id}] STDOUT (Turn Output):\n{full_stdout.strip()}")
            
            if full_stderr.strip():
                self.logger.log("CLI_AGENT", "WARNING", f"[{self.agent_id}] STDERR:\n{full_stderr.strip()}")
            
            if process.returncode != 0:
                self.logger.log("CLI_AGENT", "ERROR", f"[{self.agent_id}] Failed with code {process.returncode}")
                
            return full_stdout

    async def request(
        self, 
        messages: List[ModelMessage], 
        model_settings: Any = None, 
        model_request_parameters: Any = None
    ) -> ModelResponse:
        raise NotImplementedError

class GeminiCLIModel(CLIModel):
    @retry_async(max_attempts=3)
    async def request(
        self, 
        messages: List[ModelMessage], 
        model_settings: Any = None, 
        model_request_parameters: Any = None
    ) -> ModelResponse:
        last_message = messages[-1]
        prompt = last_message.parts[-1].content if isinstance(last_message, ModelRequest) else str(last_message)
        
        session_key = self.store.get_session(self.agent_id)
        
        cmd = list(settings.executors.gemini)
        cmd.extend(["--yolo", "--output-format", "json"])
        
        if session_key:
            cmd.extend(["--resume", session_key])
        
        # Performance: Use stdin for the prompt to handle large contexts efficiently
        # and avoid command-line argument overhead/limits.
        stdout = await self._stream_exec(cmd, input_text=prompt)
        
        response_text = ""
        new_session_id = "latest"
        
        json_objects = extract_json_objects(stdout)
        
        for payload in reversed(json_objects):
            if "response" in payload:
                response_text = payload.get("response", "")
                new_session_id = payload.get("session_id", "latest")
                break
        
        if not response_text:
            # Fallback: remove any successful JSON blocks and return the remainder
            response_text = re.sub(r'\{.*?\}', '', stdout, flags=re.DOTALL).strip()
            if not response_text:
                response_text = "The agent completed its task but returned an empty response."

        self.store.save_session(self.agent_id, str(new_session_id))
            
        return ModelResponse(parts=[TextPart(content=response_text)], timestamp=datetime.now())

class CodexCLIModel(CLIModel):
    @retry_async(max_attempts=3)
    async def request(
        self, 
        messages: List[ModelMessage], 
        model_settings: Any = None, 
        model_request_parameters: Any = None
    ) -> ModelResponse:
        last_message = messages[-1]
        prompt = last_message.parts[-1].content if isinstance(last_message, ModelRequest) else str(last_message)
        
        session_key = self.store.get_session(self.agent_id)
        is_resume = session_key is not None
        
        with tempfile.TemporaryDirectory(prefix="llmwiki-codex-") as tmp:
            output_file = Path(tmp) / "last-message.txt"
            
            cmd = list(settings.executors.codex)
            cmd.extend(["--full-auto", "--json", "--skip-git-repo-check", "-o", str(output_file)])
            
            if is_resume:
                cmd.extend(["resume", "--last"])
            else:
                cmd.append("exec")
            
            # Codex prompt via command line argument (Codex CLI usually expects this)
            cmd.append(prompt)
            
            stdout = await self._stream_exec(cmd)
            
            session_id = "last"
            json_objects = extract_json_objects(stdout)
            for payload in json_objects:
                if payload.get("type") == "session_meta":
                    session_id = payload["payload"].get("id", "last")
            
            response_text = ""
            if output_file.exists():
                response_text = output_file.read_text(encoding="utf-8")
            else:
                for payload in reversed(json_objects):
                    if payload.get("type") == "message" and payload.get("direction") == "outbound":
                        response_text = payload["payload"].get("content", "")
                        break
                if not response_text:
                    response_text = stdout
                
            self.store.save_session(self.agent_id, str(session_id))
            
            return ModelResponse(parts=[TextPart(content=response_text)], timestamp=datetime.now())
