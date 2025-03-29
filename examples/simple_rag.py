import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import yaml

from gemini_handler import (
    GeminiHandler,
    GenerationConfig,
    KeyRotationStrategy,
    Strategy,
)


class SimpleRAG:
    """A basic RAG implementation using gemini_handler with YAML configuration."""
    
    def __init__(self, config_path: str = "../config.yml"):
        """
        Initialize the RAG application with configuration from YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        # Store config path
        self.config_path = config_path
        
        # Load configuration from YAML file
        self.config = self._load_config(config_path)
        
        # Set up Gemini handler with configuration
        self.handler = self._initialize_handler()
        
        # Storage for document chunks and their embeddings
        self.documents = []
        self.embeddings = []
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'gemini' not in config:
            raise ValueError("Invalid configuration file: 'gemini' section is required")
        
        return config
    
    def _initialize_handler(self) -> GeminiHandler:
        """Initialize Gemini handler with configuration from YAML."""
        gemini_config = self.config['gemini']
        
        # Get content strategy
        content_strategy_name = gemini_config.get('strategies', {}).get('content', 'round_robin')
        content_strategy = Strategy.ROUND_ROBIN
        if content_strategy_name == "fallback":
            content_strategy = Strategy.FALLBACK
        elif content_strategy_name == "retry":
            content_strategy = Strategy.RETRY
        
        # Get key rotation strategy
        key_strategy_name = gemini_config.get('strategies', {}).get('key_rotation', 'round_robin')
        key_strategy = KeyRotationStrategy.ROUND_ROBIN
        if key_strategy_name == "sequential":
            key_strategy = KeyRotationStrategy.SEQUENTIAL
        elif key_strategy_name == "least_used":
            key_strategy = KeyRotationStrategy.LEAST_USED
        elif key_strategy_name == "smart_cooldown":
            key_strategy = KeyRotationStrategy.SMART_COOLDOWN
        
        # Get generation config
        gen_config = gemini_config.get('generation', {})
        generation_config = GenerationConfig(
            temperature=gen_config.get('temperature', 0.7),
            top_p=gen_config.get('top_p', 1.0),
            top_k=gen_config.get('top_k', 40),
            max_output_tokens=gen_config.get('max_output_tokens', 8192),
            stop_sequences=gen_config.get('stop_sequences', None),
            response_mime_type=gen_config.get('response_mime_type', "text/plain")
        )
        
        # Initialize handler
        return GeminiHandler(
            config_path=self.config_path,  # Pass the config path directly to the handler
            content_strategy=content_strategy,
            key_strategy=key_strategy,
            system_instruction=gemini_config.get('system_instruction'),
            generation_config=generation_config
        )
        
    def add_document(self, text: str, chunk_size: int = 500, overlap: int = 100):
        """
        Add a document to the RAG system, splitting it into chunks.
        
        Args:
            text: The document text
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
        """
        # Simple text chunking with overlap
        if len(text) <= chunk_size:
            chunks = [text]
        else:
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                if end < len(text) and text[end] != ' ':
                    # Try to end at a space for cleaner chunks
                    space_pos = text.rfind(' ', start, end)
                    if space_pos > start:
                        end = space_pos + 1
                
                chunks.append(text[start:end])
                start = end - overlap
        
        # Store document chunks
        self.documents.extend(chunks)
        
        # Get embedding configuration
        embedding_config = self.config['gemini'].get('embedding', {})
        embedding_model = embedding_config.get('default_model', "gemini-embedding-exp-03-07")
        task_type = embedding_config.get('task_types', {}).get('default', "SEMANTIC_SIMILARITY")
        
        # Generate embeddings for each chunk
        for chunk in chunks:
            embedding_result = self.handler.generate_embeddings(
                content=chunk,
                model_name=embedding_model,
                task_type=task_type
            )
            
            if embedding_result['success']:
                self.embeddings.append(embedding_result['embeddings'][0])
            else:
                raise RuntimeError(f"Failed to generate embedding: {embedding_result['error']}")
    
    def _compute_similarity(self, query_embedding: List[float], doc_embeddings: List[List[float]]) -> List[float]:
        """Compute cosine similarity between query and documents."""
        # Convert to numpy arrays for efficient computation
        query_array = np.array(query_embedding)
        doc_array = np.array(doc_embeddings)
        
        # Normalize vectors
        query_norm = query_array / np.linalg.norm(query_array)
        doc_norm = doc_array / np.linalg.norm(doc_array, axis=1)[:, np.newaxis]
        
        # Compute cosine similarity
        similarities = np.dot(doc_norm, query_norm)
        
        return similarities.tolist()
    
    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant document chunks for a query.
        
        Args:
            query: The user query
            top_k: Number of top documents to retrieve
            
        Returns:
            List of dictionaries with document text and similarity score
        """
        # Get embedding configuration
        embedding_config = self.config['gemini'].get('embedding', {})
        embedding_model = embedding_config.get('default_model', "gemini-embedding-exp-03-07")
        task_type = embedding_config.get('task_types', {}).get('default', "SEMANTIC_SIMILARITY")
        
        # Generate embedding for the query
        query_result = self.handler.generate_embeddings(
            content=query,
            model_name=embedding_model,
            task_type=task_type
        )
        
        if not query_result['success']:
            raise RuntimeError(f"Failed to generate query embedding: {query_result['error']}")
        
        query_embedding = query_result['embeddings'][0]
        
        # Calculate similarity scores
        similarities = self._compute_similarity(query_embedding, self.embeddings)
        
        # Get top-k documents
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return top documents with their scores
        return [
            {"text": self.documents[idx], "score": similarities[idx]}
            for idx in top_indices
        ]
    
    def answer_question(self, question: str) -> str:
        """
        Answer a question based on the document context.
        
        Args:
            question: The user's question
            
        Returns:
            Generated answer based on relevant document chunks
        """
        # Retrieve relevant document chunks
        relevant_docs = self.retrieve(question)
        
        if not relevant_docs:
            return "I don't have enough information to answer that question."
        
        # Construct prompt with context
        context = "\n\n".join([doc["text"] for doc in relevant_docs])
        
        prompt = f"""Answer the following question based only on the provided context. 
If the context doesn't contain the information needed, say "I don't have enough information to answer that question."

Context:
{context}

Question: {question}

Answer:"""
        
        # Get default model from config
        model_name = self.config['gemini'].get('default_model', "gemini-2.0-flash-exp")
        
        # Generate answer
        result = self.handler.generate_content(prompt, model_name=model_name)
        
        if result['success']:
            return result['text']
        else:
            return f"Error generating answer: {result['error']}"
