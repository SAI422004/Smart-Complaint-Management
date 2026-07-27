import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = "mysql+mysqlconnector://complaint_user:changeme@localhost:3306/complaint_db"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    rate_limit_per_minute: int = 20
    llm_model_primary: str = "llama-3.1-8b-instant"
    llm_model_large_context: str = "llama-3.3-70b-versatile"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
