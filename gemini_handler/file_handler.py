# /home/son/Documents/gemini-handler/gemini_handler/file_handler.py

import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google import genai


class FileHandler:
    """Handles file operations with the Gemini API."""

    def __init__(self, client: genai.Client):
        """
        Initialize with a Gemini API client.

        Args:
            client: An initialized Gemini API client
        """
        self.client = client

    def upload_file(
        self,
        file_path: Union[str, Path],
        display_name: Optional[str] = None  # Keep parameter for backward compatibility
    ) -> Any:
        """
        Upload a file to the Gemini API.

        Args:
            file_path: Path to the file to upload
            display_name: Optional display name (not supported by current API version)

        Returns:
            File object containing metadata for the uploaded file
        """
        file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Upload file using only supported parameters
            uploaded_file = self.client.files.upload(
                path=file_path
                # display_name parameter is not supported
            )
            
            # Log message if display_name provided but not used
            if display_name:
                print(f"Note: 'display_name' parameter is not supported by the current API version.")
                
            return uploaded_file
        except Exception as e:
            # Add original exception for better debugging context
            raise RuntimeError(f"Failed to upload file '{file_path}': {str(e)}") from e



    def get_file(self, file_name: str) -> Any:  # Using Any for genai.types.File
        """
        Get metadata for a specific file.

        Args:
            file_name: The name of the file (e.g., "files/abc-123")

        Returns:
            File object containing metadata

        Raises:
            ValueError: If the file name is invalid
            RuntimeError: If the retrieval fails
        """
        if not file_name.startswith("files/"):
            raise ValueError("File name must start with 'files/'")

        try:
            return self.client.files.get(name=file_name)
        except Exception as e:
            raise RuntimeError(f"Failed to get file metadata: {str(e)}")

    def list_files(
        self,
        page_size: int = 10,
        page_token: Optional[str] = None
    ) -> Dict:
        """
        List files owned by the requesting project.

        Args:
            page_size: Maximum number of files to return (1-100)
            page_token: Token for pagination

        Returns:
            Dictionary with 'files' list and optional 'nextPageToken'

        Raises:
            ValueError: If page_size is invalid
            RuntimeError: If the listing fails
        """
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        try:
            # The list method returns an iterator directly
            files_iterator = self.client.files.list(
                page_size=page_size,
                page_token=page_token
            )
            files = list(files_iterator) # Consume the iterator into a list

            # Note: The Python client library's list iterator handles pagination internally
            # based on page_size but doesn't expose the next page token easily in this simple list conversion.
            # If you need explicit token handling, you'd iterate differently.
            return {
                "files": files,
                "nextPageToken": None # Simplified, as the iterator handles it
            }
        except Exception as e:
            raise RuntimeError(f"Failed to list files: {str(e)}")

    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file.

        Args:
            file_name: The name of the file to delete (e.g., "files/abc-123")

        Returns:
            True if deletion was successful

        Raises:
            ValueError: If the file name is invalid
            RuntimeError: If the deletion fails
        """
        if not file_name.startswith("files/"):
            raise ValueError("File name must start with 'files/'")

        try:
            self.client.files.delete(name=file_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete file: {str(e)}")

    # This method is now effectively handled within FileOperationsMixin._generate_with_file_and_prompt_internal
    # It can be kept for direct simple use or removed if the Mixin method is always preferred.
    # If kept, it should be updated to use the correct API call structure.
    # For now, let's comment it out as the Mixin provides a more robust implementation.
    # def generate_content_with_file(
    #     self,
    #     file: Union[str, Any],
    #     prompt: str,
    #     model_name: str = "gemini-pro-vision", # Default to a vision model
    #     generation_config: Optional[Dict] = None # This config isn't directly used here
    # ) -> Dict:
    #     """
    #     Generate content using a file and prompt (Simple version).
    #     Prefer using GeminiHandler.generate_content_with_file for key rotation etc.
    #     """
    #     try:
    #         if isinstance(file, str):
    #             file_object = self.get_file(file)
    #         else:
    #             file_object = file # Assume it's already a File object

    #         # Use the client associated with this handler
    #         # Note: Does not use GenerationConfig passed as arg here
    #         model_instance = self.client.models.get(f'models/{model_name}') # Get model instance
    #         result = model_instance.generate_content(
    #             contents=[file_object, "\n\n", prompt] # Pass file object directly
    #         )

    #         return {
    #             "success": True,
    #             "text": result.text,
    #             "model": model_name,
    #             "file": file_object.name
    #         }
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "error": str(e),
    #             "model": model_name
    #         }

    def batch_upload_files(
        self,
        directory_path: Union[str, Path],
        file_extensions: Optional[List[str]] = None
    ) -> List[Any]:  # Using List[Any] for List[genai.types.File]
        """
        Upload multiple files from a directory.

        Args:
            directory_path: Path to directory containing files
            file_extensions: Optional list of file extensions to filter by (e.g., ['.jpg', '.png'])

        Returns:
            List of File objects for uploaded files

        Raises:
            FileNotFoundError: If directory doesn't exist
            RuntimeError: If uploads fail
        """
        directory = Path(directory_path)

        # Check if directory exists
        if not directory.exists() or not directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Prepare file extensions for matching (lowercase, ensure leading dot)
        processed_extensions = None
        if file_extensions:
             processed_extensions = {ext.lower() if ext.startswith('.') else '.' + ext.lower() for ext in file_extensions}


        # Filter files by extension if specified
        file_paths = []
        for f in directory.iterdir():
            if f.is_file():
                if processed_extensions:
                    if f.suffix.lower() in processed_extensions:
                        file_paths.append(f)
                else:
                     file_paths.append(f) # Upload all files if no extension filter


        # Upload each file
        uploaded_files = []
        errors = []

        for file_path in file_paths:
            try:
                # Use self.upload_file to handle individual uploads consistently
                uploaded_file = self.upload_file(file_path, display_name=file_path.name)
                uploaded_files.append(uploaded_file)
                print(f"Successfully uploaded: {file_path.name}") # Add feedback
            except Exception as e:
                error_message = f"Failed to upload {file_path.name}: {str(e)}"
                print(error_message) # Add feedback
                errors.append(error_message)


        # If there were errors, include them in the exception message
        if errors:
            error_summary = "\n".join(errors)
            # Decide whether to raise an error or just return successfully uploaded files
            # Raising an error might be better for script automation
            raise RuntimeError(f"Some files failed to upload:\n{error_summary}")

        return uploaded_files