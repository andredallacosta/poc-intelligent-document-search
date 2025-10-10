import pytest

from domain.value_objects.embedding import Embedding


class TestEmbeddingMissingCoverage:
    def test_embedding_validation_error(self):
        with pytest.raises(ValueError) as exc_info:
            Embedding(vector=[0.1, 0.2], model="test", dimensions=3)
        assert "Vector length 2 doesn't match dimensions 3" in str(exc_info.value)

    def test_cosine_similarity_zero_magnitude(self):
        zero_embedding = Embedding(vector=[0.0, 0.0, 0.0], model="test", dimensions=3)
        normal_embedding = Embedding(vector=[1.0, 2.0, 3.0], model="test", dimensions=3)
        similarity = zero_embedding.cosine_similarity(normal_embedding)
        assert similarity == 0.0
        similarity = normal_embedding.cosine_similarity(zero_embedding)
        assert similarity == 0.0

    def test_euclidean_distance_different_dimensions(self):
        embedding1 = Embedding(vector=[1.0, 2.0], model="test", dimensions=2)
        embedding2 = Embedding(vector=[1.0, 2.0, 3.0], model="test", dimensions=3)
        with pytest.raises(ValueError) as exc_info:
            embedding1.euclidean_distance(embedding2)
        assert "Cannot compare embeddings with different dimensions" in str(
            exc_info.value
        )
