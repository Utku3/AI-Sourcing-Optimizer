import logging
from typing import List, Union
from abc import ABC, abstractmethod
import pickle
from config import config

logger = logging.getLogger(__name__)

class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass

class SentenceTransformersBackend(EmbeddingBackend):
    """Sentence Transformers embedding backend."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
        except ImportError:
            raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence transformers."""
        if not text.strip():
            return [0.0] * 384  # Default dimension for all-MiniLM-L6-v2
        return self.model.encode(text).tolist()

    def get_model_name(self) -> str:
        return f"sentence-transformers-{self.model_name}"

class OpenAIBackend(EmbeddingBackend):
    """OpenAI embedding backend."""

    def __init__(self, model_name: str = "text-embedding-ada-002"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            self.model_name = model_name
        except ImportError:
            raise ImportError("openai not installed. Install with: pip install openai")

        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI backend")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        if not text.strip():
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002

        response = self.client.embeddings.create(
            input=text,
            model=self.model_name
        )
        return response.data[0].embedding

    def get_model_name(self) -> str:
        return f"openai-{self.model_name}"

class EmbeddingService:
    """Service for generating embeddings with configurable backend."""

    def __init__(self):
        self.backend = None

    def _get_backend(self) -> EmbeddingBackend:
        """Get or create the backend."""
        if self.backend is None:
            self.backend = self._create_backend()
        return self.backend

    def _create_backend(self) -> EmbeddingBackend:
        """Create the appropriate backend based on configuration."""
        backend_type = config.EMBEDDING_BACKEND.lower()

        if backend_type == "openai":
            return OpenAIBackend(config.EMBEDDING_MODEL)
        elif backend_type == "sentence-transformers":
            return SentenceTransformersBackend(config.EMBEDDING_MODEL)
        else:
            raise ValueError(f"Unsupported embedding backend: {backend_type}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text

        Returns:
            List of float values representing the embedding
        """
        try:
            return self._get_backend().generate_embedding(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {text[:100]}...: {e}")
            # Return zero vector as fallback
            return [0.0] * 384  # Safe default dimension

    def get_model_name(self) -> str:
        """Get the current model name."""
        return self._get_backend().get_model_name()

# Global embedding service instance
embedding_service = EmbeddingService()