"""
Demo script for embedding functionality in Gemini Handler.
"""
from typing import List, Optional, Union

import numpy as np

from gemini_handler import EmbeddingConfig, GeminiHandler

# Initialize handler
handler = GeminiHandler(config_path="../config.yaml")


def generate_and_print_embeddings(
    content: Union[str, List[str]],
    task_type: Optional[str] = None
) -> Union[List[float], List[List[float]]]:
    """Generate embeddings and print information about them."""
    result = handler.generate_embeddings(
        content=content,
        task_type=task_type,
        return_stats=True
    )
    
    if result['success']:
        embeddings = result['embeddings']
        
        if isinstance(content, str):
            print(f"Generated {len(embeddings)} dimensional embeddings")
            print(f"First 5 dimensions: {embeddings[:5]}")
        else:
            print(f"Generated embeddings for {len(embeddings)} texts")
            for i, embedding in enumerate(embeddings):
                if i < 2:  # Only show details for first two embeddings
                    print(f"Text {i+1}: {len(embedding)} dimensions, first 5: {embedding[:5]}")
                else:
                    print(f"Text {i+1}: {len(embedding)} dimensions")
        
        print(f"Using model: {result['model']}")
        print(f"Generation time: {result['time']:.2f} seconds")
        return embeddings
    else:
        print(f"Error: {result['error']}")
        return [] if isinstance(content, str) else [[]]


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    # Convert to numpy arrays for easier calculation
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Calculate cosine similarity
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# Generate basic embeddings
print("Basic embeddings:")
basic_embeddings = generate_and_print_embeddings("What is the meaning of life?")

# Generate embeddings optimized for semantic similarity
print("\nSemantic similarity embeddings:")
similarity_embeddings = generate_and_print_embeddings(
    "What is the meaning of life?",
    task_type=EmbeddingConfig.SEMANTIC_SIMILARITY
)

# Compare multiple texts
print("\nComparing multiple texts:")
texts = [
    "I took my dog to the vet",
    "I took my cat to the vet",
    "The stock market crashed yesterday"
]

multi_embeddings = generate_and_print_embeddings(texts)

# Calculate similarities between texts
if len(multi_embeddings) >= 3:
    sim_1_2 = calculate_cosine_similarity(multi_embeddings[0], multi_embeddings[1])
    sim_1_3 = calculate_cosine_similarity(multi_embeddings[0], multi_embeddings[3])
    sim_2_3 = calculate_cosine_similarity(multi_embeddings[1], multi_embeddings[2])
    
    print("\nCosine similarities:")
    print(f"'I took my dog to the vet' vs 'I took my cat to the vet': {sim_1_2:.4f}")
    print(f"'I took my dog to the vet' vs 'The stock market crashed yesterday': {sim_1_3:.4f}")
    print(f"'I took my cat to the vet' vs 'The stock market crashed yesterday': {sim_2_3:.4f}")
