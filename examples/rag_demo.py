import chromadb
import numpy as np

from gemini_handler import GeminiHandler


class SimpleChromaRAG:
    """Minimal RAG implementation with ChromaDB storage."""
    
    def __init__(self, config_path="../config.yaml", collection_name="documents"):
        """Initialize with config file and ChromaDB collection."""
        # Initialize Gemini handler
        self.handler = GeminiHandler(config_path=config_path)
        
        # Initialize ChromaDB
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def add_document(self, text, doc_id=None):
        """Add document to ChromaDB with Gemini embeddings."""
        # Generate a document ID if not provided
        if doc_id is None:
            doc_id = f"doc_{len(self.collection.get()['ids'])}"
        
        # Generate embedding
        result = self.handler.generate_embeddings(text)
        if not result['success']:
            raise RuntimeError(f"Embedding failed: {result['error']}")
        
        # Extract embedding values - this is the key fix
        # The embedding is returned as a ContentEmbedding object, so we need to convert it
        embedding = result['embeddings'][0]
        
        # Convert embedding to a simple list of floats
        # This handles both the case where it's already a list and when it's a ContentEmbedding object
        if hasattr(embedding, 'values'):
            embedding_list = embedding.values
        elif isinstance(embedding, list):
            embedding_list = embedding
        else:
            # Try to convert to list as a last resort
            embedding_list = list(embedding)
        
        # Add to ChromaDB
        self.collection.add(
            documents=[text],
            embeddings=[embedding_list],
            ids=[doc_id]
        )
        
        return doc_id
    
    def add_documents(self, texts, chunk_size=500):
        """Add multiple documents or chunks with simple splitting."""
        doc_ids = []
        
        # Process each text
        for i, text in enumerate(texts):
            # Simple chunking if text is too long
            if len(text) > chunk_size:
                chunks = []
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    # Try to end at a sentence boundary
                    if end < len(text):
                        for punct in ['. ', '! ', '? ']:
                            pos = text.rfind(punct, start, end)
                            if pos > start:
                                end = pos + 2
                                break
                    chunks.append(text[start:end].strip())
                    start = end
                
                # Add each chunk
                for j, chunk in enumerate(chunks):
                    doc_id = f"doc_{i}_chunk_{j}"
                    self.add_document(chunk, doc_id)
                    doc_ids.append(doc_id)
            else:
                # Add as single document
                doc_id = self.add_document(text, f"doc_{i}")
                doc_ids.append(doc_id)
        
        return doc_ids
    
    def answer_question(self, question, n_results=2):
        """Answer question based on retrieved documents."""
        # Generate question embedding
        q_result = self.handler.generate_embeddings(question)
        if not q_result['success']:
            return f"Error: {q_result['error']}"
        
        # Extract query embedding values
        q_embedding = q_result['embeddings'][0]
        if hasattr(q_embedding, 'values'):
            q_embedding_list = q_embedding.values
        elif isinstance(q_embedding, list):
            q_embedding_list = q_embedding
        else:
            q_embedding_list = list(q_embedding)
        
        # Query ChromaDB for similar documents
        results = self.collection.query(
            query_embeddings=[q_embedding_list],
            n_results=n_results
        )
        
        # Extract documents
        if not results['documents'][0]:
            return "I don't have enough information to answer that question."
        
        # Create context from retrieved documents
        context = "\n\n".join(results['documents'][0])
        
        # Generate answer
        prompt = f"""Answer the following question based only on the provided context.
If the context doesn't contain enough information, say "I don't have enough information to answer that question."

Context:
{context}

Question: {question}

Answer:"""
        
        result = self.handler.generate_content(prompt)
        return result['text'] if result['success'] else f"Error: {result['error']}"


# Example usage
if __name__ == "__main__":
    # Create RAG instance
    rag = SimpleChromaRAG(config_path="../config.yaml")
    
    # Add document paragraphs
    paragraphs = [
        "The Python programming language was created by Guido van Rossum and was first released in 1991. It is known for its readability and simplicity, making it an excellent choice for beginners.",
        "Python is a multi-paradigm programming language. Object-oriented programming and structured programming are fully supported, and many of its features support functional programming and aspect-oriented programming."
    ]
    rag.add_documents(paragraphs)
    
    # Answer question
    answer = rag.answer_question("When was Python first released and who created it?")
    print(f"Answer: {answer}")
