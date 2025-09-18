import time
from typing import Dict, List

from application.dto.chat_dto import (
    ChatRequestDTO,
    ChatResponseDTO,
    DocumentReferenceDTO,
)
from application.interfaces.llm_service import LLMServiceInterface
from domain.exceptions.chat_exceptions import ChatError
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from domain.value_objects.embedding import Embedding


class ChatWithDocumentsUseCase:

    def __init__(
        self,
        chat_service: ChatService,
        search_service: SearchService,
        llm_service: LLMServiceInterface,
    ):
        self._chat_service = chat_service
        self._search_service = search_service
        self._llm_service = llm_service

    async def execute(self, request: ChatRequestDTO) -> ChatResponseDTO:
        start_time = time.time()

        try:
            # Get or create session
            if request.session_id:
                session = await self._chat_service.get_session(request.session_id)
            else:
                session = await self._chat_service.create_session()

            # Add user message to session
            user_message = await self._chat_service.add_user_message(
                session_id=session.id,
                content=request.message,
                metadata=request.metadata,
            )

            # Generate embedding for search
            query_embedding_vector = await self._llm_service.generate_embedding(
                request.message
            )
            query_embedding = Embedding.from_openai(query_embedding_vector)

            # Search for relevant documents
            search_results = await self._search_service.search_similar_content(
                query_embedding=query_embedding, n_results=5, similarity_threshold=0.7
            )

            # Convert search results to document references
            document_references = self._search_service.convert_results_to_references(
                search_results
            )

            # Get conversation history
            conversation_history = await self._chat_service.get_conversation_history(
                session_id=session.id, limit=10
            )

            # Prepare context for LLM
            llm_messages = self._prepare_llm_context(
                user_message=request.message,
                search_results=search_results,
                conversation_history=conversation_history,
            )

            # Generate response using LLM
            llm_response = await self._llm_service.generate_response(
                messages=llm_messages, temperature=0.7, max_tokens=1000
            )

            # Add assistant message to session
            assistant_message = await self._chat_service.add_assistant_message(
                session_id=session.id,
                content=llm_response["content"],
                document_references=document_references,
                metadata={
                    "token_usage": llm_response.get("usage", {}),
                    "model": llm_response.get("model", "gpt-4o-mini"),
                    "search_results_count": len(search_results),
                },
            )

            # Convert document references to DTOs
            source_dtos = [
                DocumentReferenceDTO(
                    document_id=ref.document_id,
                    chunk_id=ref.chunk_id,
                    source=ref.source,
                    page=ref.page,
                    similarity_score=ref.similarity_score,
                    excerpt=ref.excerpt,
                )
                for ref in document_references
            ]

            processing_time = time.time() - start_time

            return ChatResponseDTO(
                response=llm_response["content"],
                session_id=session.id,
                sources=source_dtos,
                metadata={
                    "message_id": str(assistant_message.id),
                    "search_results_count": len(search_results),
                    "conversation_length": len(conversation_history)
                    + 2,  # +2 for current exchange
                },
                processing_time=processing_time,
                token_usage=llm_response.get("usage"),
            )

        except Exception as e:
            raise ChatError(f"Failed to process chat request: {e}")

    def _prepare_llm_context(
        self, user_message: str, search_results: List, conversation_history: List
    ) -> List[Dict[str, str]]:
        messages = []

        # System message with context
        context_parts = []
        if search_results:
            context_parts.append("Documentos relevantes encontrados:")
            for i, result in enumerate(search_results[:3], 1):
                chunk = result.chunk
                context_parts.append(f"{i}. {chunk.content[:200]}...")

        system_message = f"""Você é um assistente especializado em responder perguntas baseadas em documentos.

{chr(10).join(context_parts) if context_parts else "Nenhum documento relevante encontrado."}

Instruções:
- Responda baseado nos documentos fornecidos
- Cite as fontes quando relevante
- Se não houver informação suficiente, diga isso claramente
- Seja conciso e objetivo
- Use linguagem natural e amigável"""

        messages.append({"role": "system", "content": system_message})

        # Add conversation history (last 5 exchanges)
        for message in conversation_history[-10:]:
            messages.append({"role": message.role.value, "content": message.content})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages
