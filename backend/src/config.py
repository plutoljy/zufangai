"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API配置
    openai_api_key: str
    deepseek_api_key: str
    anthropic_api_key: Optional[str] = None

    # DeepSeek 配置
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 千问 Embedding 配置
    embedding_api_key: str = "sk-69c3840a434d42f1a1ded0b52d02fec7"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v1"
    
    # JWT配置
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    
    # 服务配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    
    # 文件上传
    max_file_size: int = 52428800  # 50MB
    upload_dir: str = "data/uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
