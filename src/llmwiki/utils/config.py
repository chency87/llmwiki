import os
import tomllib
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PathSettings(BaseModel):
    vault: str = "vault"

class LLMSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: Optional[str] = None
    api_key: Optional[str] = None

class ExecutorSettings(BaseModel):
    gemini: List[str] = Field(default_factory=lambda: ["gemini"])
    codex: List[str] = Field(default_factory=lambda: ["codex"])

class IngestSettings(BaseModel):
    concurrency: int = 5
    max_parallel_extractors: int = 4

class LoggingSettings(BaseModel):
    level: str = "INFO"
    file_max_bytes: int = 5242880 # 5MB
    file_backup_count: int = 5

class RuntimeSettings(BaseModel):
    read_cache_size: int = 128
    maintenance_interval_s: int = 3600

class DashboardSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8501

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 1313

class TelegramSettings(BaseModel):
    token: Optional[str] = None
    allowed_users: List[str] = Field(default_factory=list)

class RestSettings(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: Optional[str] = None

class GatewaySettings(BaseModel):
    enabled: bool = False
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    rest: RestSettings = Field(default_factory=RestSettings)
    feishu: Dict[str, Any] = Field(default_factory=dict)

class MCPServerSettings(BaseModel):
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)

class MCPSettings(BaseModel):
    servers: Dict[str, MCPServerSettings] = Field(default_factory=dict)

class Settings(BaseModel):
    paths: PathSettings = Field(default_factory=PathSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    executors: ExecutorSettings = Field(default_factory=ExecutorSettings)
    ingest: IngestSettings = Field(default_factory=IngestSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """
        Loads settings from a TOML file. 
        Priority: Specified path -> ./llmwiki.toml -> vault/.llmwiki/llmwiki.toml -> Defaults.
        """
        search_paths = []
        if config_path:
            search_paths.append(config_path)
        
        search_paths.extend([
            "llmwiki.toml",
            os.path.join("vault", ".llmwiki", "llmwiki.toml")
        ])

        for path in search_paths:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        data = tomllib.load(f)
                        return cls.model_validate(data)
                except Exception as e:
                    print(f"Warning: Failed to load config from {path}: {e}")
        
        return cls()

# Singleton instance
settings = Settings.load()
