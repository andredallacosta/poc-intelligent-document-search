import time
from typing import Dict, List

from application.dto.chat_dto import (
    ChatRequestDTO,
    ChatResponseDTO,
    DocumentReferenceDTO,
)
from application.interfaces.llm_service import LLMServiceInterface
from domain.exceptions.chat_exceptions import ChatError
from domain.exceptions.token_exceptions import (
    MunicipalityInactiveError,
    TokenLimitExceededError,
)
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from domain.services.token_limit_service import TokenLimitService
from domain.value_objects.embedding import Embedding
from domain.value_objects.municipality_id import MunicipalityId


class ChatWithDocumentsUseCase:

    def __init__(
        self,
        chat_service: ChatService,
        search_service: SearchService,
        llm_service: LLMServiceInterface,
        token_limit_service: TokenLimitService,
    ):
        self._chat_service = chat_service
        self._search_service = search_service
        self._llm_service = llm_service
        self._token_limit_service = token_limit_service

    async def execute(self, request: ChatRequestDTO) -> ChatResponseDTO:
        start_time = time.time()

        try:
            # 1. Manage session (existing)
            if request.session_id:
                session = await self._chat_service.get_session(request.session_id)
            else:
                session = await self._chat_service.create_session()

            # 2. NEW: Extract municipality from session/user
            municipality_id = await self._extract_municipality_id(session)

            # 3. NEW: Pre-check token availability (fast)
            if not await self._token_limit_service.has_available_tokens(
                municipality_id
            ):
                raise TokenLimitExceededError("Token limit exceeded for this period")

            # 4. Add user message (existing)
            await self._chat_service.add_user_message(
                session_id=session.id,
                content=request.message,
                metadata=request.metadata,
            )

            # 5. Generate embedding for search (existing)
            query_embedding_vector = await self._llm_service.generate_embedding(
                request.message
            )
            query_embedding = Embedding.from_openai(query_embedding_vector)

            # 6. Search similar documents (existing)
            search_results = await self._search_service.search_similar_content(
                query=request.message, query_embedding=query_embedding, n_results=5
            )

            document_references = self._search_service.convert_results_to_references(
                search_results
            )

            # 7. Prepare conversation context (existing)
            conversation_history = await self._chat_service.get_conversation_history(
                session_id=session.id, limit=10
            )

            llm_messages = self._prepare_llm_context(
                user_message=request.message,
                search_results=search_results,
                conversation_history=conversation_history,
            )

            # 8. Call LLM (existing)
            llm_response = await self._llm_service.generate_response(
                messages=llm_messages, temperature=0.7, max_tokens=1000
            )

            # 9. NEW: Register actual token consumption atomically
            tokens_consumed = llm_response.get("usage", {}).get("total_tokens", 0)
            if tokens_consumed > 0:
                await self._token_limit_service.consume_tokens_atomically(
                    municipality_id=municipality_id,
                    tokens_consumed=tokens_consumed,
                    metadata={
                        "session_id": str(session.id),
                        "message_length": len(request.message),
                        "search_results_count": len(search_results),
                        "model": llm_response.get("model", "gpt-4o-mini"),
                    },
                )

            # 10. Save assistant response with token audit (UPDATED)
            assistant_message = await self._chat_service.add_assistant_message(
                session_id=session.id,
                content=llm_response["content"],
                document_references=document_references,
                metadata={
                    "token_usage": llm_response.get("usage", {}),
                    "model": llm_response.get("model", "gpt-4o-mini"),
                    "search_results_count": len(search_results),
                    # NEW: Integrated token audit
                    "token_audit": {
                        "municipality_id": str(municipality_id.value),
                        "tokens_consumed": tokens_consumed,
                        "timestamp": time.time(),
                    },
                },
            )

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
                    "conversation_length": len(conversation_history) + 2,
                },
                processing_time=processing_time,
                token_usage=llm_response.get("usage"),
            )

        except TokenLimitExceededError:
            # Specific error for token limit
            raise
        except MunicipalityInactiveError:
            # Specific error for inactive municipality
            raise
        except Exception as e:
            # Other errors (existing)
            processing_time = time.time() - start_time
            raise ChatError(f"Failed to process chat request: {e}")

    def _prepare_llm_context(
        self, user_message: str, search_results: List, conversation_history: List
    ) -> List[Dict[str, str]]:
        messages = []

        context_parts = []
        if search_results:
            context_parts.append("Documentos relevantes encontrados:")
            for i, result in enumerate(search_results[:3], 1):
                chunk = result.chunk
                context_parts.append(f"{i}. {chunk.content[:200]}...")

        system_message = f"""
            Você é um assistente especializado em responder perguntas
            baseadas em documentos.
            {chr(10).join(context_parts) if context_parts else 'Nenhum documento relevante encontrado.'}

            Instruções:
            - Responda baseado nos documentos fornecidos
            - Cite as fontes quando relevante
            - Se não houver informação suficiente, diga isso claramente
            - Seja conciso e objetivo
            - Use linguagem natural e amigável"""

        messages.append({"role": "system", "content": system_message})

        for message in conversation_history[-10:]:
            messages.append({"role": message.role.value, "content": message.content})

        messages.append({"role": "user", "content": user_message})

        return messages

    async def _extract_municipality_id(self, session) -> MunicipalityId:
        """Extracts municipality_id from session/user"""
        if hasattr(session, "user_id") and session.user_id:
            # Authenticated user - find municipality
            # TODO: Implement user service lookup when available
            # user = await self._user_service.get_by_id(session.user_id)
            # if user and user.municipality_id:
            #     return user.municipality_id
            pass

        # Anonymous user or without municipality - use default municipality
        # (can be configurable or raise error depending on business rule)
        return MunicipalityId.from_string(
            "123e4567-e89b-12d3-a456-426614174000"
        )  # Configure as needed
