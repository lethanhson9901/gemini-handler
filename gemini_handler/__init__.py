# Modified __init__.py

# gemini_handler/__init__.py
from .content_generation import ContentGenerationMixin
from .data_models import (
    EmbeddingConfig,
    GenerationConfig,
    KeyRotationStrategy,
    KeyStats,
    ModelConfig,
    ModelResponse,
    Strategy,
)
from .file_handler import FileHandler
from .file_operations import FileOperationsMixin
from .gemini_handler import GeminiHandler
from .proxy import ProxyManager  # Add this import

__all__ = [
    'GeminiHandler',
    'GenerationConfig',
    'EmbeddingConfig',
    'ModelResponse',
    'Strategy',
    'KeyRotationStrategy',
    'KeyStats',
    'ModelConfig',
    'FileHandler',
    'ContentGenerationMixin',
    'FileOperationsMixin',
    'ProxyManager'  # Add this export
]
