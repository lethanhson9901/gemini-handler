# gemini_handler/data_models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class Strategy(Enum):
    """Available content generation strategies."""
    ROUND_ROBIN = "round_robin"
    FALLBACK = "fallback"
    RETRY = "retry"


class KeyRotationStrategy(Enum):
    """Available key rotation strategies."""
    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"
    SMART_COOLDOWN = "smart_cooldown"


@dataclass
class KeyStats:
    """Track usage statistics for each API key."""
    uses: int = 0
    last_used: float = 0
    failures: int = 0
    rate_limited_until: float = 0


@dataclass
class GenerationConfig:
    """Configuration for model generation parameters."""
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = 40
    max_output_tokens: int = 8192
    stop_sequences: Optional[List[str]] = None
    response_mime_type: str = "text/plain"
    response_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    task_type: Optional[str] = None
    
    # Task type constants
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    QUESTION_ANSWERING = "QUESTION_ANSWERING"
    FACT_VERIFICATION = "FACT_VERIFICATION"
    CODE_RETRIEVAL_QUERY = "CODE_RETRIEVAL_QUERY"


@dataclass
class ModelResponse:
    """Represents a standardized response from any model."""
    success: bool
    model: str
    text: str = ""
    error: str = ""
    time: float = 0.0
    attempts: int = 1
    api_key_index: int = 0
    structured_data: Optional[Dict[str, Any]] = None
    embeddings: Optional[Union[List[float], List[List[float]]]] = None
    file_info: Optional[Dict[str, Any]] = None  # Added field for file information


class ModelConfig:
    """Configuration for model settings."""
    def __init__(self):
        self.models = [
            "gemini-2.0-flash",
            "gemini-2.5-pro-exp-03-25",
            "gemini-2.0-flash-lite",
            "gemini-2.0-pro-exp-02-05",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-embedding-exp-03-07",
            "imagen-3.0-generate-002",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-exp-1206",
            "gemini-pro-vision",
            "gemini-1.5-flash-001-tuning",
            "gemini-1.5-flash-8b-exp-0827",
            "gemini-1.5-flash-8b-exp-0924",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-exp-image-generation",
            "gemini-2.0-flash-lite-preview-02-05",
            "gemini-2.0-flash-lite-preview",
            "gemini-2.0-pro-exp",
            "gemini-2.0-flash-thinking-exp",
            "gemini-2.0-flash-thinking-exp-1219",
            "gemini-embedding-exp"           
        ]
        self.max_retries = 3
        self.retry_delay = 30
        self.default_model = self.models[0] if self.models else "gemini-2.0-flash"
        self.default_embedding_model = "gemini-embedding-exp-03-07"
