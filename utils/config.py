from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="12345678", env="NEO4J_PASSWORD")
    
    class Config:
        env_file = ".env"

settings = Settings()

# 添加导出声明
__all__ = ['settings']