from typing import Any, Dict, List

from application.interfaces.llm_service import LLMServiceInterface
from domain.exceptions.chat_exceptions import LLMError
from infrastructure.external.openai_client import OpenAIClient


class LLMServiceImpl(LLMServiceInterface):

    def __init__(self, openai_client: OpenAIClient):
        self._openai_client = openai_client

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        try:
            return await self._openai_client.generate_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMError(f"Failed to generate response: {e}")

    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        try:
            async for chunk in self._openai_client.generate_streaming_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
        except Exception as e:
            raise LLMError(f"Failed to generate streaming response: {e}")

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            embedding = await self._openai_client.generate_embedding(text)
            return embedding.vector
        except Exception as e:
            raise LLMError(f"Failed to generate embedding: {e}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            embeddings = await self._openai_client.generate_embeddings_batch(texts)
            return [embedding.vector for embedding in embeddings]
        except Exception as e:
            raise LLMError(f"Failed to generate batch embeddings: {e}")
