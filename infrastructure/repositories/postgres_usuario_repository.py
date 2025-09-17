from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
import logging

from domain.entities.usuario import Usuario
from domain.value_objects.usuario_id import UsuarioId
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.repositories.usuario_repository import UsuarioRepository
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from infrastructure.database.models import UsuarioModel

logger = logging.getLogger(__name__)


class PostgresUsuarioRepository(UsuarioRepository):
    """Implementação PostgreSQL do repositório de Usuario"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, usuario: Usuario) -> Usuario:
        """Salva um usuário"""
        try:
            model = UsuarioModel(
                id=usuario.id.value,
                prefeitura_id=usuario.prefeitura_id.value if usuario.prefeitura_id else None,
                nome=usuario.nome,
                email=usuario.email,
                senha_hash=usuario.senha_hash,
                ativo=usuario.ativo,
                criado_em=usuario.criado_em,
                atualizado_em=usuario.atualizado_em
            )
            
            self._session.add(model)
            await self._session.flush()
            
            return usuario
            
        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower() and "email" in str(e).lower():
                raise BusinessRuleViolationError(f"Usuário com email '{usuario.email}' já existe")
            raise BusinessRuleViolationError(f"Erro ao salvar usuário: {e}")
    
    async def find_by_id(self, usuario_id: UsuarioId) -> Optional[Usuario]:
        """Busca usuário por ID"""
        stmt = select(UsuarioModel).where(UsuarioModel.id == usuario_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_by_email(self, email: str) -> Optional[Usuario]:
        """Busca usuário por email"""
        stmt = select(UsuarioModel).where(UsuarioModel.email == email.strip().lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_by_prefeitura_id(
        self, 
        prefeitura_id: PrefeituraId, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[Usuario]:
        """Busca usuários de uma prefeitura"""
        stmt = select(UsuarioModel).where(UsuarioModel.prefeitura_id == prefeitura_id.value)
        stmt = stmt.order_by(UsuarioModel.nome)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_all_active(self, limit: Optional[int] = None, offset: int = 0) -> List[Usuario]:
        """Lista todos os usuários ativos"""
        stmt = select(UsuarioModel).where(UsuarioModel.ativo == True)
        stmt = stmt.order_by(UsuarioModel.nome)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Usuario]:
        """Lista todos os usuários"""
        stmt = select(UsuarioModel).order_by(UsuarioModel.nome)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_anonimos(self, limit: Optional[int] = None, offset: int = 0) -> List[Usuario]:
        """Lista usuários anônimos (sem prefeitura)"""
        stmt = select(UsuarioModel).where(UsuarioModel.prefeitura_id.is_(None))
        stmt = stmt.order_by(UsuarioModel.criado_em.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def update(self, usuario: Usuario) -> Usuario:
        """Atualiza um usuário"""
        try:
            stmt = update(UsuarioModel).where(
                UsuarioModel.id == usuario.id.value
            ).values(
                prefeitura_id=usuario.prefeitura_id.value if usuario.prefeitura_id else None,
                nome=usuario.nome,
                email=usuario.email,
                senha_hash=usuario.senha_hash,
                ativo=usuario.ativo,
                atualizado_em=usuario.atualizado_em
            )
            
            result = await self._session.execute(stmt)
            
            if result.rowcount == 0:
                raise BusinessRuleViolationError(f"Usuário {usuario.id} não encontrado")
            
            return usuario
            
        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower() and "email" in str(e).lower():
                raise BusinessRuleViolationError(f"Usuário com email '{usuario.email}' já existe")
            raise BusinessRuleViolationError(f"Erro ao atualizar usuário: {e}")
    
    async def delete(self, usuario_id: UsuarioId) -> bool:
        """Remove um usuário"""
        stmt = delete(UsuarioModel).where(UsuarioModel.id == usuario_id.value)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def exists(self, usuario_id: UsuarioId) -> bool:
        """Verifica se usuário existe"""
        stmt = select(func.count(UsuarioModel.id)).where(UsuarioModel.id == usuario_id.value)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    async def exists_by_email(self, email: str) -> bool:
        """Verifica se existe usuário com o email"""
        stmt = select(func.count(UsuarioModel.id)).where(UsuarioModel.email == email.strip().lower())
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    async def count(self) -> int:
        """Conta total de usuários"""
        stmt = select(func.count(UsuarioModel.id))
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def count_active(self) -> int:
        """Conta usuários ativos"""
        stmt = select(func.count(UsuarioModel.id)).where(UsuarioModel.ativo == True)
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def count_by_prefeitura(self, prefeitura_id: PrefeituraId) -> int:
        """Conta usuários de uma prefeitura"""
        stmt = select(func.count(UsuarioModel.id)).where(UsuarioModel.prefeitura_id == prefeitura_id.value)
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def count_anonimos(self) -> int:
        """Conta usuários anônimos"""
        stmt = select(func.count(UsuarioModel.id)).where(UsuarioModel.prefeitura_id.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar()
    
    def _model_to_entity(self, model: UsuarioModel) -> Usuario:
        """Converte model para entidade"""
        return Usuario(
            id=UsuarioId.from_uuid(model.id),
            prefeitura_id=PrefeituraId.from_uuid(model.prefeitura_id) if model.prefeitura_id else None,
            nome=model.nome,
            email=model.email,
            senha_hash=model.senha_hash,
            ativo=model.ativo,
            criado_em=model.criado_em,
            atualizado_em=model.atualizado_em
        )
