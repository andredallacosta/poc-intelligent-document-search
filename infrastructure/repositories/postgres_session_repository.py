from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
import logging

from domain.entities.chat_session import ChatSession
from domain.entities.message import Message, MessageRole, MessageType, DocumentReference
from domain.repositories.session_repository import SessionRepository, MessageRepository
from domain.exceptions.chat_exceptions import SessionNotFoundError
from domain.value_objects.usuario_id import UsuarioId
from infrastructure.database.models import ChatSessionModel, MessageModel

logger = logging.getLogger(__name__)


class PostgresSessionRepository(SessionRepository):
    """Implementação PostgreSQL do repositório de sessões"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save_session(self, session: ChatSession) -> ChatSession:
        """Salva uma sessão"""
        try:
            model = ChatSessionModel(
                id=session.id,
                usuario_id=session.usuario_id.value if session.usuario_id else None,
                ativo=session.is_active,
                meta_data=session.metadata,
                criado_em=session.created_at,
                atualizado_em=session.updated_at
            )
            
            self._session.add(model)
            await self._session.flush()
            
            return session
            
        except IntegrityError as e:
            await self._session.rollback()
            raise SessionNotFoundError(f"Erro ao salvar sessão: {e}")
    
    async def find_session_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        """Busca sessão por ID"""
        stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_active_sessions(self, limit: Optional[int] = None) -> List[ChatSession]:
        """Busca sessões ativas"""
        stmt = select(ChatSessionModel).where(ChatSessionModel.ativo == True)
        stmt = stmt.order_by(ChatSessionModel.atualizado_em.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Remove uma sessão"""
        stmt = delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def deactivate_session(self, session_id: UUID) -> bool:
        """Desativa uma sessão"""
        stmt = update(ChatSessionModel).where(
            ChatSessionModel.id == session_id
        ).values(ativo=False)
        
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def session_exists(self, session_id: UUID) -> bool:
        """Verifica se sessão existe"""
        stmt = select(func.count(ChatSessionModel.id)).where(ChatSessionModel.id == session_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    def _model_to_entity(self, model: ChatSessionModel) -> ChatSession:
        """Converte model para entidade"""
        return ChatSession(
            id=model.id,
            usuario_id=UsuarioId.from_uuid(model.usuario_id) if model.usuario_id else None,
            messages=[],  # Messages são carregadas separadamente
            created_at=model.criado_em,
            updated_at=model.atualizado_em,
            is_active=model.ativo,
            metadata=model.meta_data or {}
        )


class PostgresMessageRepository(MessageRepository):
    """Implementação PostgreSQL do repositório de mensagens"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save_message(self, message: Message) -> Message:
        """Salva uma mensagem"""
        try:
            model = MessageModel(
                id=message.id,
                session_id=message.session_id,
                role=message.role.value,
                conteudo=message.content,
                tipo_mensagem=message.message_type.value,
                referencias_documento=self._references_to_dict(message.document_references),
                tokens_usados=0,  # Será implementado quando tivermos controle de tokens
                meta_data=message.metadata,
                criado_em=message.created_at
            )
            
            self._session.add(model)
            await self._session.flush()
            
            return message
            
        except IntegrityError as e:
            await self._session.rollback()
            raise SessionNotFoundError(f"Erro ao salvar mensagem: {e}")
    
    async def find_message_by_id(self, message_id: UUID) -> Optional[Message]:
        """Busca mensagem por ID"""
        stmt = select(MessageModel).where(MessageModel.id == message_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_messages_by_session_id(
        self, 
        session_id: UUID, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Busca mensagens de uma sessão"""
        stmt = select(MessageModel).where(MessageModel.session_id == session_id)
        stmt = stmt.order_by(MessageModel.criado_em)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def delete_messages_by_session_id(self, session_id: UUID) -> int:
        """Remove mensagens de uma sessão"""
        stmt = delete(MessageModel).where(MessageModel.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.rowcount
    
    async def count_messages_by_session_id(self, session_id: UUID) -> int:
        """Conta mensagens de uma sessão"""
        stmt = select(func.count(MessageModel.id)).where(MessageModel.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar()
    
    def _references_to_dict(self, references: List[DocumentReference]) -> List[dict]:
        """Converte referências para dict"""
        return [
            {
                "chunk_id": str(ref.chunk_id),
                "document_id": str(ref.document_id),
                "source": ref.source,
                "similarity_score": ref.similarity_score,
                "excerpt": ref.excerpt
            }
            for ref in references
        ]
    
    def _dict_to_references(self, data: List[dict]) -> List[DocumentReference]:
        """Converte dict para referências"""
        references = []
        for item in data:
            ref = DocumentReference(
                chunk_id=UUID(item["chunk_id"]),
                document_id=UUID(item["document_id"]),
                source=item["source"],
                similarity_score=item.get("similarity_score"),
                excerpt=item.get("excerpt")
            )
            references.append(ref)
        return references
    
    def _model_to_entity(self, model: MessageModel) -> Message:
        """Converte model para entidade"""
        return Message(
            id=model.id,
            session_id=model.session_id,
            role=MessageRole(model.role),
            content=model.conteudo,
            message_type=MessageType(model.tipo_mensagem),
            document_references=self._dict_to_references(model.referencias_documento or []),
            metadata=model.meta_data or {},
            created_at=model.criado_em
        )
