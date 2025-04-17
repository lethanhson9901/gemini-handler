# tests/integration/test_file_handling.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from gemini_handler.gemini_handler import GeminiHandler


class TestFileHandling:
    """Integration tests for file handling workflows"""
    
    @patch('gemini_handler.file_operations.genai')
    @patch('gemini_handler.file_handler.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_file_upload_workflow(self, mock_google_genai, mock_file_genai, mock_op_genai, sample_image_path):
        """Test the file upload workflow"""
        # Mock client
        mock_client = MagicMock()
        mock_file = MagicMock()
        mock_file.name = "files/test-file"
        mock_file.uri = "https://example.com/files/test-file"
        mock_file.mime_type = "image/png"
        mock_client.files.upload.return_value = mock_file
        mock_google_genai.Client.return_value = mock_client
        
        # Create handler
        handler = GeminiHandler(api_keys=["test1", "test2"])
        
        # Upload file
        result = handler.upload_file(file_path=sample_image_path)
        
        # Verify results
        assert result["success"] is True
        assert result["name"] == "files/test-file"
        assert result["uri"] == "https://example.com/files/test-file"
        assert result["mime_type"] == "image/png"
        
        # Verify API was called
        mock_client.files.upload.assert_called_with(path=sample_image_path)
    
    @patch('gemini_handler.file_operations.genai')
    @patch('gemini_handler.gemini_handler.google_genai')
    def test_generate_with_file_workflow(self, mock_google_genai, mock_genai, mock_genai_response):
        """Test the generate with file workflow"""
        # Mock client and file
        mock_client = MagicMock()
        mock_file = MagicMock()
        mock_file.name = "files/test-file"
        mock_file.uri = "https://example.com/files/test-file"
        mock_file.mime_type = "image/png"
        mock_client.files.get.return_value = mock_file
        mock_google_genai.Client.return_value = mock_client
        
        # Mock generation response
        import requests
        from io import BytesIO
        from PIL import Image
        
        # Mock requests get
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b'dummy_image_content'
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            # Mock PIL Image open
            with patch('PIL.Image.open') as mock_open:
                mock_image = MagicMock()
                mock_open.return_value = mock_image
                
                # Mock model
                mock_model = MagicMock()
                mock_model.generate_content.return_value = mock_genai_response
                mock_genai.GenerativeModel.return_value = mock_model
                
                # Create handler
                handler = GeminiHandler(api_keys=["test1", "test2"])
                
                # Generate with file
                result = handler.generate_content_with_file(
                    file="files/test-file",
                    prompt="Describe this image",
                    model_name="gemini-1.5-pro"
                )
                
                # Verify results
                assert result["success"] is True
                assert result["model"] == "gemini-1.5-pro"
                assert result["text"] == mock_genai_response.text
                assert result["file_info"]["name"] == "files/test-file"
                
                # Verify API calls
                mock_client.files.get.assert_called_with(name="files/test-file")
                mock_get.assert_called_once()
                mock_model.generate_content.assert_called_once()
