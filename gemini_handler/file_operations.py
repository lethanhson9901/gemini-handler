# /home/son/Documents/gemini-handler/gemini_handler/file_operations.py

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# Import data models explicitly to avoid circular import issues
from .data_models import GenerationConfig, ModelResponse
from .response_handler import ResponseHandler


class FileOperationsMixin:
    """Mixin for file operations methods."""

    def _get_file_object(self, file: Union[str, Any]) -> Any:
        """Helper to get the file object, retrieving if necessary."""
        if isinstance(file, str):
            # Assumes file is a file name like "files/xyz"
            return self.file_handler.get_file(file)
        # Assume it's already a File object (or compatible)
        return file

    def _generate_with_file_and_prompt_internal(
        self,
        file: Union[str, Any],
        prompt: str,
        model_name: str,
        generation_config: GenerationConfig,
        system_instruction: Optional[str] = None
    ) -> ModelResponse:
        """Internal helper to generate content with file, handling keys and response."""
        start_time = time.time()
        api_key, key_index = self.key_manager.get_next_key()

        try:
            # Retrieve the actual File object if a name was passed
            file_object = self._get_file_object(file)
            file_info = {
                "name": file_object.name,
                "mime_type": getattr(file_object, 'mime_type', None)
            }

            # Configure API key
            genai.configure(api_key=api_key)

            # Create the generative model instance
            gen_config_dict = generation_config.to_dict()
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=gen_config_dict,
                system_instruction=system_instruction or self.system_instruction
            )

            # Handle file conversion - we need to download and convert to a format
            # acceptable by the generate_content method
            if hasattr(file_object, 'uri') and file_object.uri:
                # Need to import necessary libraries for downloading and processing
                from io import BytesIO

                import requests
                from PIL import Image

                # Get appropriate URI for download
                uri = file_object.download_uri if hasattr(file_object, 'download_uri') and file_object.download_uri else file_object.uri
                
                # Download file content
                headers = {"Authorization": f"Bearer {api_key}"} if "googleapis.com" in uri else {}
                response = requests.get(uri, headers=headers)
                response.raise_for_status()
                
                # Process file based on MIME type
                mime_type = getattr(file_object, 'mime_type', '')
                if mime_type and mime_type.startswith('image/'):
                    # For images, convert to PIL Image which is accepted by genai
                    file_content = Image.open(BytesIO(response.content))
                else:
                    # For other file types, you might need different handling
                    # depending on what the genai API accepts
                    raise ValueError(f"Unsupported file MIME type: {mime_type}")
                    
                # Generate content with properly formatted content
                response = model.generate_content([file_content, "\n\n", prompt])
            else:
                raise ValueError(f"File object does not have a URI: {file_object.name}")

            # Process response
            result = ResponseHandler.process_response(
                response,
                model_name,
                start_time,
                key_index,
                generation_config.response_mime_type
            )

            if result.success:
                self.key_manager.mark_success(key_index)
            
            # Add file info to the result
            result.file_info = file_info
            return result

        except Exception as e:
            if "429" in str(e):
                self.key_manager.mark_rate_limited(key_index)
                error_message = f"Rate limit exceeded: {str(e)}"
            else:
                self.key_manager.mark_failure(key_index)
                error_message = f"An unexpected error occurred: {str(e)}"
                
            return ModelResponse(
                success=False,
                model=model_name,
                error=error_message,
                time=time.time() - start_time,
                api_key_index=key_index,
                file_info={"name": getattr(file, 'name', str(file))}
            )

    # --- Existing File Operations (Upload, Get, List, Delete, Batch Upload) ---

    def upload_file(
        self,
        file_path: Union[str, Path],
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to the Gemini API.
        Uses self.file_handler internally.
        """
        try:
            # Use the FileHandler instance associated with GeminiHandler
            file = self.file_handler.upload_file(file_path, display_name)
            return {
                "success": True,
                "file": file, # Return the raw file object
                "name": file.name,
                "display_name": getattr(file, 'display_name', None),
                "uri": getattr(file, 'uri', None),
                "mime_type": getattr(file, 'mime_type', None),
                "size_bytes": getattr(file, 'size_bytes', None),
                "state": getattr(file, 'state', None)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_file(self, file_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific file.
        Uses self.file_handler internally.
        """
        try:
            file = self.file_handler.get_file(file_name)
            return {
                "success": True,
                "file": file, # Return the raw file object
                "name": file.name,
                "display_name": getattr(file, 'display_name', None),
                "uri": getattr(file, 'uri', None),
                "mime_type": getattr(file, 'mime_type', None),
                "size_bytes": getattr(file, 'size_bytes', None),
                "state": getattr(file, 'state', None)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_files(
        self,
        page_size: int = 10,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List files owned by the requesting project.
        Uses self.file_handler internally.
        """
        try:
            result = self.file_handler.list_files(page_size, page_token)
            # Convert file objects to dicts for simpler JSON serialization if needed later
            files_list = [
                {
                    "name": f.name,
                    "display_name": getattr(f, 'display_name', None),
                    "uri": getattr(f, 'uri', None),
                    "mime_type": getattr(f, 'mime_type', None),
                    "size_bytes": getattr(f, 'size_bytes', None),
                    "state": getattr(f, 'state', None)
                } for f in result["files"]
            ]
            return {
                "success": True,
                "files": files_list,
                "next_page_token": result.get("nextPageToken")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_file(self, file_name: str) -> Dict[str, Any]:
        """
        Delete a file.
        Uses self.file_handler internally.
        """
        try:
            success = self.file_handler.delete_file(file_name)
            return {
                "success": success,
                "deleted_file": file_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def batch_upload_files(
        self,
        directory_path: Union[str, Path],
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple files from a directory.
        Uses self.file_handler internally.
        """
        try:
            files = self.file_handler.batch_upload_files(directory_path, file_extensions)
             # Convert file objects to dicts for simpler JSON serialization if needed later
            files_list = [
                {
                    "name": f.name,
                    "display_name": getattr(f, 'display_name', None),
                    "uri": getattr(f, 'uri', None),
                    "mime_type": getattr(f, 'mime_type', None),
                    "size_bytes": getattr(f, 'size_bytes', None),
                    "state": getattr(f, 'state', None)
                } for f in files
            ]
            return {
                "success": True,
                "files": files_list,
                "count": len(files_list)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # --- Modified and New Generation Methods ---

    def generate_content_with_file(
        self,
        file: Union[str, Any],  # Can be file name or File object
        prompt: str,
        model_name: Optional[str] = None,
        return_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text content using a file and prompt.
        This now uses the internal helper for consistency.
        """
        if not model_name:
            # Ensure a vision-capable model is selected
            model_name = "gemini-1.5-pro"  # Default to a vision-capable model

        # Use default text generation config
        gen_config = GenerationConfig()  # Plain text output

        # Call the internal unified method
        response_obj = self._generate_with_file_and_prompt_internal(
            file=file,
            prompt=prompt,
            model_name=model_name,
            generation_config=gen_config,
        )

        # Convert ModelResponse object back to dictionary for external interface
        result_dict = response_obj.__dict__

        # Add key stats if requested
        if return_stats:
            result_dict["key_stats"] = self.get_key_stats()  # Use existing method

        return result_dict

    def generate_structured_content_with_file(
        self,
        file: Union[str, Any],  # Can be file name or File object
        prompt: str,
        schema: Dict[str, Any],
        model_name: Optional[str] = None,
        return_stats: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate structured content (JSON) using a file, prompt, and schema.
        """
        if not model_name:
            # Suggest or default to a model known for function calling / structured output with vision
            model_name = "gemini-2.0-flash"  # Use a vision-capable model
            print(f"Warning: No model_name specified, defaulting to '{model_name}' for structured output with file.")

        # Create a structured generation config based on current config + overrides
        original_config = self.generation_config  # Get base config from handler instance

        structured_config = GenerationConfig(
            temperature=temperature if temperature is not None else original_config.temperature,
            top_p=top_p if top_p is not None else original_config.top_p,
            top_k=top_k if top_k is not None else original_config.top_k,
            max_output_tokens=max_output_tokens if max_output_tokens is not None else original_config.max_output_tokens,
            stop_sequences=original_config.stop_sequences,  # Inherit stop sequences
            response_mime_type="application/json",  # CRUCIAL for structured output
            response_schema=schema  # CRUCIAL for structured output
        )

        # Call the internal unified method
        response_obj = self._generate_with_file_and_prompt_internal(
            file=file,
            prompt=prompt,
            model_name=model_name,
            generation_config=structured_config,
        )

        # Convert ModelResponse object back to dictionary for external interface
        result_dict = response_obj.__dict__

        # Add key stats if requested
        if return_stats:
            result_dict["key_stats"] = self.get_key_stats()  # Use existing method

        return result_dict

    def generate_with_local_file(
        self,
        file_path: Union[str, Path],
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        return_stats: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate content using a local file directly without uploading first."""
        import os

        from PIL import Image
        
        start_time = time.time()
        file_path = Path(file_path)
        
        # Verify file exists
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "time": time.time() - start_time
            }
        
        try:
            # Get API key
            api_key, key_index = self.key_manager.get_next_key()
            
            # Configure with API key
            genai.configure(api_key=api_key)
            
            # Determine if structured output is needed
            use_structured = schema is not None
            
            # Create generation config
            original_config = self.generation_config
            if use_structured:
                gen_config = GenerationConfig(
                    temperature=temperature if temperature is not None else original_config.temperature,
                    top_p=top_p if top_p is not None else original_config.top_p,
                    top_k=top_k if top_k is not None else original_config.top_k,
                    max_output_tokens=max_output_tokens if max_output_tokens is not None else original_config.max_output_tokens,
                    stop_sequences=original_config.stop_sequences,
                    response_mime_type="application/json",
                    response_schema=schema
                )
            else:
                gen_config = GenerationConfig(
                    temperature=temperature if temperature is not None else original_config.temperature,
                    top_p=top_p if top_p is not None else original_config.top_p,
                    top_k=top_k if top_k is not None else original_config.top_k,
                    max_output_tokens=max_output_tokens if max_output_tokens is not None else original_config.max_output_tokens,
                    stop_sequences=original_config.stop_sequences
                )
            
            # Select appropriate model
            if not model_name:
                # Default to a vision-capable model
                model_name = "gemini-1.5-pro"
            
            # Create model instance
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=gen_config.to_dict(),
                system_instruction=self.system_instruction
            )
            
            # Load the file directly based on file type
            file_extension = file_path.suffix.lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                # Open image file directly
                image = Image.open(file_path)
                # Generate content with image
                response = model.generate_content([image, "\n\n", prompt])
            else:
                # For other file types, handle accordingly
                # Currently just supporting images
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_extension}",
                    "time": time.time() - start_time,
                    "api_key_index": key_index
                }
            
            # Process response
            result = ResponseHandler.process_response(
                response,
                model_name,
                start_time,
                key_index,
                gen_config.response_mime_type
            )
            
            # Mark success
            if result.success:
                self.key_manager.mark_success(key_index)
            
            # Add file info
            result.file_info = {
                "name": str(file_path),
                "is_local": True,
                "size_bytes": os.path.getsize(file_path)
            }
            
            # Convert to dictionary
            result_dict = result.__dict__
            
            # Add key stats if requested
            if return_stats:
                result_dict["key_stats"] = self.get_key_stats()
            
            return result_dict
            
        except Exception as e:
            if "429" in str(e):
                self.key_manager.mark_rate_limited(key_index)
                error_message = f"Rate limit exceeded: {str(e)}"
            else:
                self.key_manager.mark_failure(key_index)
                error_message = f"An unexpected error occurred: {str(e)}"
                
            return {
                "success": False,
                "model": model_name if 'model_name' in locals() else "unknown",
                "error": error_message,
                "time": time.time() - start_time,
                "api_key_index": key_index if 'key_index' in locals() else 0,
                "file_info": {"name": str(file_path), "is_local": True}
            }
