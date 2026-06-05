from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load .env file and override existing system environment variables
load_dotenv(override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocMind AI"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "change_me_in_production_please_use_openssl_rand_hex_32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = "sqlite:///./cda_v3.db"
    
    # AI / External APIs
    GEMINI_API_KEY: Optional[str] = None
    NVIDIA_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Gemini Model Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    
    # Storage
    PDF_UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "pdfs")
    CHROMA_DB_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
    
    # Email Settings (SMTP)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = "noreply@docmind.ai"
    EMAILS_FROM_NAME: Optional[str] = "DocMind AI"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

