from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass(frozen=True)
class Embedding:
    vector: List[float]
    model: str
    dimensions: int

    def __post_init__(self):
        if len(self.vector) != self.dimensions:
            raise ValueError(
                f"Vector length {len(self.vector)} doesn't match dimensions {self.dimensions}"
            )

    @property
    def magnitude(self) -> float:
        return float(np.linalg.norm(self.vector))

    def cosine_similarity(self, other: "Embedding") -> float:
        if self.dimensions != other.dimensions:
            raise ValueError("Cannot compare embeddings with different dimensions")

        dot_product = np.dot(self.vector, other.vector)
        magnitude_product = self.magnitude * other.magnitude

        if magnitude_product == 0:
            return 0.0

        return float(dot_product / magnitude_product)

    def euclidean_distance(self, other: "Embedding") -> float:
        if self.dimensions != other.dimensions:
            raise ValueError("Cannot compare embeddings with different dimensions")

        return float(np.linalg.norm(np.array(self.vector) - np.array(other.vector)))

    @classmethod
    def from_openai(cls, vector: List[float]) -> "Embedding":
        return cls(
            vector=vector, model="text-embedding-3-small", dimensions=len(vector)
        )

    def to_dict(self) -> dict:
        return {
            "vector": self.vector,
            "model": self.model,
            "dimensions": self.dimensions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Embedding":
        return cls(
            vector=data["vector"], model=data["model"], dimensions=data["dimensions"]
        )
