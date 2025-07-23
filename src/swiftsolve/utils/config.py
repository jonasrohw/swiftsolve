from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import os, json

class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    max_iterations: int = 3
    diminish_delta: float = 0.05
    sandbox_timeout_sec: int = 2
    sandbox_mem_mb: int = 512
    log_dir: str = "logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()  # env vars automatically picked up