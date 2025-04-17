# tests/unit/test_gemini_handler.py
import pytest
from unittest.mock import patch, MagicMock

from gemini_handler.gemini_handler import GeminiHandler
from gemini_handler.data_models import (
    GenerationConfig, KeyRotationStrategy, Strategy
)


class TestGeminiHandler:
    """Tests for the GeminiHandler class"""
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_init_with_api_keys(self, mock_google_genai, mock_genai):
        """Test initialization with explicit API keys"""
        api_keys = ["test1", "test2"]
        handler = GeminiHandler(api_keys=api_keys)
        
        assert handler.api_keys == api_keys
        assert len(handler.key_manager.api_keys) == 2
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    @patch('gemini_handler.config.ConfigLoader.load_api_keys')
    def test_init_with_config_path(self, mock_load_keys, mock_google_genai, mock_genai):
        """Test initialization with config path"""
        mock_load_keys.return_value = ["config1", "config2"]
        mock_google_genai.Client.return_value = MagicMock()
        
        handler = GeminiHandler(config_path="test_config.yaml")
        
        mock_load_keys.assert_called_once_with("test_config.yaml")
        assert handler.api_keys == ["config1", "config2"]
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_strategy_creation(self, mock_google_genai, mock_genai):
        """Test strategy creation based on strategy enum"""
        mock_google_genai.Client.return_value = MagicMock()
        
        # Round Robin
        handler = GeminiHandler(
            api_keys=["test1", "test2"],
            content_strategy=Strategy.ROUND_ROBIN
        )
        assert handler._strategy.__class__.__name__ == "RoundRobinStrategy"
        
        # Fallback
        handler = GeminiHandler(
            api_keys=["test1", "test2"],
            content_strategy=Strategy.FALLBACK
        )
        assert handler._strategy.__class__.__name__ == "FallbackStrategy"
        
        # Retry
        handler = GeminiHandler(
            api_keys=["test1", "test2"],
            content_strategy=Strategy.RETRY
        )
        assert handler._strategy.__class__.__name__ == "RetryStrategy"
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_get_key_stats(self, mock_google_genai, mock_genai):
        """Test getting key statistics"""
        mock_google_genai.Client.return_value = MagicMock()
        
        handler = GeminiHandler(api_keys=["test1", "test2"])
        
        # Set some dummy stats
        handler.key_manager.key_stats[0].uses = 5
        handler.key_manager.key_stats[1].uses = 10
        
        # Get all stats
        stats = handler.get_key_stats()
        assert len(stats) == 2
        assert stats[0]["uses"] == 5
        assert stats[1]["uses"] == 10
        
        # Get specific key stats
        stats = handler.get_key_stats(key_index=1)
        assert len(stats) == 1
        assert 1 in stats
        assert stats[1]["uses"] == 10
        
        # Invalid key index
        with pytest.raises(ValueError):
            handler.get_key_stats(key_index=99)
