# tests/integration/test_content_generation.py
import pytest
from unittest.mock import patch, MagicMock

from gemini_handler.gemini_handler import GeminiHandler


class TestContentGeneration:
    """Integration tests for content generation workflows"""
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_generate_content_workflow(self, mock_google_genai, mock_genai, mock_genai_response):
        """Test the complete content generation workflow"""
        mock_google_genai.Client.return_value = MagicMock()
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_genai_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create handler
        handler = GeminiHandler(api_keys=["test1", "test2"])
        
        # Generate content
        result = handler.generate_content(
            prompt="Test prompt",
            model_name="gemini-2.0-flash",
            return_stats=True
        )
        
        # Verify results
        assert result["success"] is True
        assert result["model"] == "gemini-2.0-flash"
        assert result["text"] == mock_genai_response.text
        assert "key_stats" in result
        
        # Verify API was called with correct parameters
        mock_genai.configure.assert_called()
        mock_genai.GenerativeModel.assert_called_with(
            model_name="gemini-2.0-flash",
            generation_config=handler.generation_config.to_dict(),
            system_instruction=handler.system_instruction
        )
        mock_model.generate_content.assert_called_with("Test prompt")
    
    @patch('gemini_handler.strategies.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_generate_structured_content_workflow(self, mock_google_genai, mock_genai, mock_genai_response):
        """Test the structured content generation workflow"""
        mock_google_genai.Client.return_value = MagicMock()
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_genai_response
        mock_genai_response.text = '{"name": "Test", "value": 42}'
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create handler
        handler = GeminiHandler(api_keys=["test1", "test2"])
        
        # Define schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            }
        }
        
        # Generate structured content
        result = handler.generate_structured_content(
            prompt="Test prompt",
            schema=schema,
            model_name="gemini-2.0-flash"
        )
        
        # Verify results
        assert result["success"] is True
        assert result["model"] == "gemini-2.0-flash"
        assert result["text"] == '{"name": "Test", "value": 42}'
        assert result["structured_data"] == {"name": "Test", "value": 42}
