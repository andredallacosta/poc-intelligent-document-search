import pytest
import numpy as np
from typing import List

from domain.value_objects.embedding import Embedding

class TestEmbedding:
    
    def test_create_embedding_from_openai(self):
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding = Embedding.from_openai(vector)
        
        assert embedding.vector == vector
        assert embedding.dimensions == 5
        assert embedding.model == "text-embedding-3-small"
    
    def test_create_embedding_custom(self):
        vector = [0.1, 0.2, 0.3]
        embedding = Embedding(vector=vector, model="custom-model", dimensions=3)
        
        assert embedding.vector == vector
        assert embedding.dimensions == 3
        assert embedding.model == "custom-model"
    
    def test_embedding_similarity_identical_vectors(self):
        vector = [1.0, 0.0, 0.0]
        embedding1 = Embedding.from_openai(vector)
        embedding2 = Embedding.from_openai(vector)
        
        similarity = embedding1.cosine_similarity(embedding2)
        
        assert similarity == pytest.approx(1.0, abs=1e-6)
    
    def test_embedding_similarity_orthogonal_vectors(self):
        vector1 = [1.0, 0.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]
        embedding1 = Embedding.from_openai(vector1)
        embedding2 = Embedding.from_openai(vector2)
        
        similarity = embedding1.cosine_similarity(embedding2)
        
        assert similarity == pytest.approx(0.0, abs=1e-6)
    
    def test_embedding_similarity_opposite_vectors(self):
        vector1 = [1.0, 0.0, 0.0]
        vector2 = [-1.0, 0.0, 0.0]
        embedding1 = Embedding.from_openai(vector1)
        embedding2 = Embedding.from_openai(vector2)
        
        similarity = embedding1.cosine_similarity(embedding2)
        
        assert similarity == pytest.approx(-1.0, abs=1e-6)
    
    def test_embedding_similarity_different_dimensions_raises_error(self):
        embedding1 = Embedding.from_openai([1.0, 0.0])
        embedding2 = Embedding.from_openai([1.0, 0.0, 0.0])
        
        with pytest.raises(ValueError, match="Cannot compare embeddings with different dimensions"):
            embedding1.cosine_similarity(embedding2)
    
    def test_embedding_distance(self):
        vector1 = [1.0, 0.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]
        embedding1 = Embedding.from_openai(vector1)
        embedding2 = Embedding.from_openai(vector2)
        
        distance = embedding1.euclidean_distance(embedding2)
        
        assert distance == pytest.approx(np.sqrt(2), abs=1e-6)
    
    def test_embedding_magnitude(self):
        vector = [3.0, 4.0]
        embedding = Embedding.from_openai(vector)
        
        magnitude = embedding.magnitude
        
        assert magnitude == pytest.approx(5.0, abs=1e-6)
    
    def test_embedding_magnitude_calculation(self):
        vector = [3.0, 4.0]
        embedding = Embedding.from_openai(vector)
        
        assert embedding.magnitude == pytest.approx(5.0, abs=1e-6)
    
    def test_embedding_zero_magnitude(self):
        vector = [0.0, 0.0, 0.0]
        embedding = Embedding.from_openai(vector)
        
        assert embedding.magnitude == pytest.approx(0.0, abs=1e-6)
    
    def test_embedding_to_dict(self):
        vector = [0.1, 0.2, 0.3]
        embedding = Embedding.from_openai(vector)
        
        result = embedding.to_dict()
        
        expected = {
            "vector": vector,
            "dimensions": 3,
            "model": "text-embedding-3-small"
        }
        assert result == expected
    
    def test_embedding_from_dict(self):
        data = {
            "vector": [0.1, 0.2, 0.3],
            "dimensions": 3,
            "model": "text-embedding-3-small"
        }
        
        embedding = Embedding.from_dict(data)
        
        assert embedding.vector == [0.1, 0.2, 0.3]
        assert embedding.dimensions == 3
        assert embedding.model == "text-embedding-3-small"
    
    def test_embedding_equality(self):
        vector = [0.1, 0.2, 0.3]
        embedding1 = Embedding.from_openai(vector)
        embedding2 = Embedding.from_openai(vector)
        embedding3 = Embedding.from_openai([0.1, 0.2, 0.4])
        
        assert embedding1 == embedding2
        assert embedding1 != embedding3
    
    def test_embedding_repr(self):
        vector = [0.1, 0.2, 0.3]
        embedding = Embedding.from_openai(vector)
        
        repr_str = repr(embedding)
        
        assert "Embedding" in repr_str
        assert "dimensions=3" in repr_str
        assert "text-embedding-3-small" in repr_str
