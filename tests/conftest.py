# tests/conftest.py
import os
import pytest
from unittest.mock import MagicMock, patch
import yaml
from pathlib import Path
import time

import google.generativeai as genai
from google import genai as google_genai

from gemini_handler.data_models import (
    GenerationConfig, KeyRotationStrategy, ModelConfig, ModelResponse, Strategy
)
from gemini_handler.key_rotation import KeyRotationManager


# Load test configuration
@pytest.fixture(scope="session")
def test_config():
    """Load test configuration from test_config.yaml"""
    config_path = Path(__file__).parent / "test_config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {
        "api_keys": ["test-key-1", "test-key-2", "test-key-3"],
        "gemini": {
            "default_model": "gemini-2.0-flash"
        }
    }


# Mock fixtures for GoogleGenerativeAI components
@pytest.fixture
def mock_genai_response():
    """Mock response from Google GenerativeAI"""
    response = MagicMock()
    response.text = "This is a mock response from Gemini."
    response.candidates = [MagicMock()]
    response.candidates[0].finish_reason = 1  # Normal finish
    return response


@pytest.fixture
def mock_genai_error_response():
    """Mock error response for rate limiting"""
    def _create_error(status_code=429, message="Rate limit exceeded"):
        error = MagicMock()
        error.status_code = status_code
        error.message = message
        return error
    return _create_error


@pytest.fixture
def mock_genai_client(mock_genai_response):
    """Mock Gemini client"""
    client = MagicMock()
    
    # Mock files API
    files = MagicMock()
    file = MagicMock()
    file.name = "files/test-file"
    file.uri = "https://example.com/files/test-file"
    file.mime_type = "image/png"
    
    files.upload.return_value = file
    files.get.return_value = file
    files.list.return_value = [file]
    
    client.files = files
    
    # Mock models API
    model = MagicMock()
    model.generate_content.return_value = mock_genai_response
    
    models = MagicMock()
    models.get.return_value = model
    models.embed_content.return_value = MagicMock(
        embeddings=[[0.1, 0.2, 0.3]]
    )
    
    client.models = models
    
    return client


@pytest.fixture
def mock_genai_generate_content(mock_genai_response):
    """Mock for GenerativeModel.generate_content"""
    with patch('google.generativeai.GenerativeModel.generate_content', 
               return_value=mock_genai_response) as mock:
        yield mock


@pytest.fixture
def key_manager():
    """Create a KeyRotationManager with test keys"""
    return KeyRotationManager(
        api_keys=["test-key-1", "test-key-2", "test-key-3"],
        strategy=KeyRotationStrategy.ROUND_ROBIN
    )


@pytest.fixture
def model_config():
    """Create a ModelConfig for testing"""
    config = ModelConfig()
    config.models = ["gemini-2.0-flash", "gemini-1.5-pro"]
    config.max_retries = 2
    config.retry_delay = 0.1  # Short delay for testing
    return config


@pytest.fixture
def generation_config():
    """Create a GenerationConfig for testing"""
    return GenerationConfig(
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_output_tokens=1024
    )


# Sample image fixture
@pytest.fixture
def sample_image_path(tmp_path):
    """Create a small blank image for testing"""
    try:
        from PIL import Image
        
        # Create test images directory if it doesn't exist
        test_img_dir = Path(__file__).parent / "test_data" / "images"
        test_img_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test image file
        img_path = test_img_dir / "test_image.png"
        if not img_path.exists():
            img = Image.new('RGB', (100, 100), color='white')
            img.save(img_path)
        
        return img_path
    except ImportError:
        # If PIL is not installed, create a simple text file instead
        test_file_dir = Path(__file__).parent / "test_data" / "files"
        test_file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = test_file_dir / "test_file.txt"
        if not file_path.exists():
            with open(file_path, 'w') as f:
                f.write("This is a test file")
        
        return file_path
