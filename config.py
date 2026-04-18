import os
from typing import Optional

class Config:
    """Configuration class for the raw material substitution system."""

    # Qwen API configuration
    QWEN_API_KEY: Optional[str] = os.getenv("QWEN_API_KEY")
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://api.qwen.ai/v1")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-turbo")

    # Embedding configuration
    EMBEDDING_BACKEND: str = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")  # or "openai"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Ollama remote model configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://134.199.196.115:11434")
    OLLAMA_MODEL_NAME: str = os.getenv("OLLAMA_MODEL_NAME", "qwen2.5-72b")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "db.sqlite")

    # Allowed classes for Qwen
    ALLOWED_CLASSES: list[str] = [
        "acidulant",
        "antioxidant",
        "colorant",
        "emulsifier",
        "flavor",
        "preservative",
        "stabilizer",
        "sweetener",
        "thickener",
        "vitamin",
        "mineral",
        "protein",
        "fat",
        "carbohydrate",
        "fiber",
        "enzyme",
        "other"
    ]

# Global config instance
config = Config()