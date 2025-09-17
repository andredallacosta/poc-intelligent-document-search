from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
import logging

from domain.entities.prefeitura import Prefeitura
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.repositories.prefeitura_repository import PrefeituraRepository
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from infrastructure.database.models import PrefeituraModel

logger = logging.getLogger(__name__)


class PostgresPrefeituraRepository(PrefeituraRepository):
    """Implementação PostgreSQL do repositório de Prefeitura"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, prefeitura: Prefeitura) -> Prefeitura:
        """Salva uma prefeitura"""
        try:
            model = PrefeituraModel(
                id=prefeitura.id.value,
                nome=prefeitura.nome,
                quota_tokens=prefeitura.quota_tokens,
                tokens_consumidos=prefeitura.tokens_consumidos,
                ativo=prefeitura.ativo,
                criado_em=prefeitura.criado_em,
                atualizado_em=prefeitura.atualizado_em
            )
            
            self._session.add(model)
            await self._session.flush()
            
            return prefeitura
            
        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                raise BusinessRuleViolationError(f"Prefeitura com nome '{prefeitura.nome}' já existe")
            raise BusinessRuleViolationError(f"Erro ao salvar prefeitura: {e}")
    
    async def find_by_id(self, prefeitura_id: PrefeituraId) -> Optional[Prefeitura]:
        """Busca prefeitura por ID"""
        stmt = select(PrefeituraModel).where(PrefeituraModel.id == prefeitura_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_by_nome(self, nome: str) -> Optional[Prefeitura]:
        """Busca prefeitura por nome"""
        stmt = select(PrefeituraModel).where(PrefeituraModel.nome == nome.strip())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def find_all_active(self, limit: Optional[int] = None, offset: int = 0) -> List[Prefeitura]:
        """Lista todas as prefeituras ativas"""
        stmt = select(PrefeituraModel).where(PrefeituraModel.ativo == True)
        stmt = stmt.order_by(PrefeituraModel.nome)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Prefeitura]:
        """Lista todas as prefeituras"""
        stmt = select(PrefeituraModel).order_by(PrefeituraModel.nome)
        
        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def update(self, prefeitura: Prefeitura) -> Prefeitura:
        """Atualiza uma prefeitura"""
        try:
            stmt = update(PrefeituraModel).where(
                PrefeituraModel.id == prefeitura.id.value
            ).values(
                nome=prefeitura.nome,
                quota_tokens=prefeitura.quota_tokens,
                tokens_consumidos=prefeitura.tokens_consumidos,
                ativo=prefeitura.ativo,
                atualizado_em=prefeitura.atualizado_em
            )
            
            result = await self._session.execute(stmt)
            
            if result.rowcount == 0:
                raise BusinessRuleViolationError(f"Prefeitura {prefeitura.id} não encontrada")
            
            return prefeitura
            
        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                raise BusinessRuleViolationError(f"Prefeitura com nome '{prefeitura.nome}' já existe")
            raise BusinessRuleViolationError(f"Erro ao atualizar prefeitura: {e}")
    
    async def delete(self, prefeitura_id: PrefeituraId) -> bool:
        """Remove uma prefeitura"""
        stmt = delete(PrefeituraModel).where(PrefeituraModel.id == prefeitura_id.value)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def exists(self, prefeitura_id: PrefeituraId) -> bool:
        """Verifica se prefeitura existe"""
        stmt = select(func.count(PrefeituraModel.id)).where(PrefeituraModel.id == prefeitura_id.value)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    async def exists_by_nome(self, nome: str) -> bool:
        """Verifica se existe prefeitura com o nome"""
        stmt = select(func.count(PrefeituraModel.id)).where(PrefeituraModel.nome == nome.strip())
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    async def count(self) -> int:
        """Conta total de prefeituras"""
        stmt = select(func.count(PrefeituraModel.id))
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def count_active(self) -> int:
        """Conta prefeituras ativas"""
        stmt = select(func.count(PrefeituraModel.id)).where(PrefeituraModel.ativo == True)
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def find_by_quota_critica(self, percentual_limite: float = 90.0) -> List[Prefeitura]:
        """Busca prefeituras com quota crítica (próxima do limite)"""
        # Calcula percentual: (tokens_consumidos / quota_tokens) * 100 >= percentual_limite
        stmt = select(PrefeituraModel).where(
            and_(
                PrefeituraModel.ativo == True,
                PrefeituraModel.quota_tokens > 0,
                (PrefeituraModel.tokens_consumidos * 100.0 / PrefeituraModel.quota_tokens) >= percentual_limite
            )
        ).order_by(PrefeituraModel.nome)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def find_by_quota_esgotada(self) -> List[Prefeitura]:
        """Busca prefeituras com quota esgotada"""
        stmt = select(PrefeituraModel).where(
            and_(
                PrefeituraModel.ativo == True,
                PrefeituraModel.tokens_consumidos >= PrefeituraModel.quota_tokens
            )
        ).order_by(PrefeituraModel.nome)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: PrefeituraModel) -> Prefeitura:
        """Converte model para entidade"""
        return Prefeitura(
            id=PrefeituraId.from_uuid(model.id),
            nome=model.nome,
            quota_tokens=model.quota_tokens,
            tokens_consumidos=model.tokens_consumidos,
            ativo=model.ativo,
            criado_em=model.criado_em,
            atualizado_em=model.atualizado_em
        )
