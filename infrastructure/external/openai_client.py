import os
from typing import List

import openai
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from domain.exceptions.chat_exceptions import LLMError
from domain.exceptions.document_exceptions import EmbeddingError
from domain.value_objects.embedding import Embedding

load_dotenv()


class OpenAIClient:

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=self.api_key
        )

        self.client = openai.OpenAI(api_key=self.api_key)

    async def generate_embedding(self, text: str) -> Embedding:
        try:
            vector = self.embeddings.embed_query(text)
            return Embedding.from_openai(vector)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
        try:
            vectors = self.embeddings.embed_documents(texts)
            return [Embedding.from_openai(vector) for vector in vectors]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}")

    async def generate_chat_completion(
        self,
        messages: List[dict],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
            }
        except Exception as e:
            raise LLMError(f"Failed to generate chat completion: {e}")

    async def generate_streaming_completion(
        self,
        messages: List[dict],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise LLMError(f"Failed to generate streaming completion: {e}")

    def estimate_tokens(self, text: str) -> int:
        return len(text.split()) * 1.3  # Rough estimation

    def calculate_embedding_cost(self, token_count: int) -> float:
        return (token_count / 1_000_000) * 0.02  # $0.02 per 1M tokens

    def calculate_completion_cost(
        self, prompt_tokens: int, completion_tokens: int
    ) -> float:
        prompt_cost = (prompt_tokens / 1_000_000) * 0.00015  # GPT-4o-mini input
        completion_cost = (completion_tokens / 1_000_000) * 0.0006  # GPT-4o-mini output
        return prompt_cost + completion_cost
