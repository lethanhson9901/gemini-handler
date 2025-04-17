# tests/unit/test_response_handler.py
import time
import pytest
from unittest.mock import MagicMock

from gemini_handler.data_models import ModelResponse
from gemini_handler.response_handler import ResponseHandler


class TestResponseHandler:
    """Tests for the ResponseHandler class"""
    
    def test_process_response_success(self, mock_genai_response):
        """Test processing a successful response"""
        model_name = "test-model"
        start_time = time.time()
        key_index = 0
        
        result = ResponseHandler.process_response(
            mock_genai_response, 
            model_name, 
            start_time, 
            key_index
        )
        
        assert isinstance(result, ModelResponse)
        assert result.success is True
        assert result.model == model_name
        assert result.text == mock_genai_response.text
        assert result.api_key_index == key_index
    
    def test_process_response_copyright(self):
        """Test processing a response with copyright material"""
        model_name = "test-model"
        start_time = time.time()
        key_index = 0
        
        # Create response with copyright material
        response = MagicMock()
        response.candidates = [MagicMock()]
        response.candidates[0].finish_reason = 4  # Copyright material
        
        result = ResponseHandler.process_response(
            response, 
            model_name, 
            start_time, 
            key_index
        )
        
        assert isinstance(result, ModelResponse)
        assert result.success is False
        assert result.model == model_name
        assert "Copyright material" in result.error
        assert result.api_key_index == key_index
    
    def test_process_response_json(self):
        """Test processing a JSON structured response"""
        model_name = "test-model"
        start_time = time.time()
        key_index = 0
        
        # Create response with JSON content
        response = MagicMock()
        response.text = '{"key": "value", "number": 42}'
        response.candidates = [MagicMock()]
        response.candidates[0].finish_reason = 1  # Normal finish
        
        result = ResponseHandler.process_response(
            response, 
            model_name, 
            start_time, 
            key_index,
            response_mime_type="application/json"
        )
        
        assert isinstance(result, ModelResponse)
        assert result.success is True
        assert result.model == model_name
        assert result.structured_data == {"key": "value", "number": 42}
    
    def test_process_response_invalid_json(self):
        """Test processing an invalid JSON response"""
        model_name = "test-model"
        start_time = time.time()
        key_index = 0
        
        # Create response with invalid JSON content
        response = MagicMock()
        response.text = '{"key": "value", invalid json'
        response.candidates = [MagicMock()]
        response.candidates[0].finish_reason = 1  # Normal finish
        
        result = ResponseHandler.process_response(
            response, 
            model_name, 
            start_time, 
            key_index,
            response_mime_type="application/json"
        )
        
        assert isinstance(result, ModelResponse)
        assert result.success is False
        assert result.model == model_name
        assert "Failed to parse JSON" in result.error
