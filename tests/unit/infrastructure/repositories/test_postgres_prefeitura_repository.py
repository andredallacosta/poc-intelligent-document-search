import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.prefeitura import Prefeitura
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.prefeitura_id import PrefeituraId
from infrastructure.repositories.postgres_prefeitura_repository import PostgresPrefeituraRepository
from infrastructure.database.models import PrefeituraModel


class TestPostgresPrefeituraRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresPrefeituraRepository(mock_session)
    
    @pytest.fixture
    def sample_prefeitura(self):
        return Prefeitura(
            id=PrefeituraId.from_uuid(uuid4()),
            nome="Prefeitura de Teste",
            quota_tokens=10000,
            tokens_consumidos=5000,
            ativo=True,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow()
        )

    def test_init(self, mock_session):
        repo = PostgresPrefeituraRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_success(self, repository, mock_session, sample_prefeitura):
        mock_session.flush = AsyncMock()
        
        result = await repository.save(sample_prefeitura)
        
        assert result == sample_prefeitura
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_unique_constraint_error(self, repository, mock_session, sample_prefeitura):
        mock_session.flush.side_effect = IntegrityError("unique constraint", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="já existe"):
            await repository.save(sample_prefeitura)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_other_integrity_error(self, repository, mock_session, sample_prefeitura):
        mock_session.flush.side_effect = IntegrityError("other error", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="Erro ao salvar prefeitura"):
            await repository.save(sample_prefeitura)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_found(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_by_id(sample_prefeitura.id)
        
        assert result == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_id(PrefeituraId.from_uuid(uuid4()))
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_nome_found(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_by_nome("Prefeitura de Teste")
        
        assert result == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_by_nome_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_nome("Inexistente")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_active_success(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_all_active()
        
        assert len(result) == 1
        assert result[0] == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_all_active_with_pagination(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_all_active(limit=10, offset=5)
        
        assert len(result) == 1
        assert result[0] == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_all_active_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_all_active()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_find_all_success(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_all()
        
        assert len(result) == 1
        assert result[0] == sample_prefeitura

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session, sample_prefeitura):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.update(sample_prefeitura)
        
        assert result == sample_prefeitura
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_session, sample_prefeitura):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(BusinessRuleViolationError, match="não encontrada"):
            await repository.update(sample_prefeitura)

    @pytest.mark.asyncio
    async def test_update_unique_constraint_error(self, repository, mock_session, sample_prefeitura):
        mock_session.execute.side_effect = IntegrityError("unique constraint", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="já existe"):
            await repository.update(sample_prefeitura)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(PrefeituraId.from_uuid(uuid4()))
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(PrefeituraId.from_uuid(uuid4()))
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists(PrefeituraId.from_uuid(uuid4()))
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists(PrefeituraId.from_uuid(uuid4()))
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_nome_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_nome("Teste")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_nome_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_nome("Inexistente")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_count_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        result = await repository.count()
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_active_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result
        
        result = await repository.count_active()
        
        assert result == 3

    @pytest.mark.asyncio
    async def test_find_by_quota_critica_success(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_by_quota_critica(90.0)
        
        assert len(result) == 1
        assert result[0] == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_by_quota_critica_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_quota_critica()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_quota_esgotada_success(self, repository, mock_session, sample_prefeitura):
        mock_model = Mock(spec=PrefeituraModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_prefeitura):
            result = await repository.find_by_quota_esgotada()
        
        assert len(result) == 1
        assert result[0] == sample_prefeitura

    @pytest.mark.asyncio
    async def test_find_by_quota_esgotada_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_quota_esgotada()
        
        assert result == []

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=PrefeituraModel)
        mock_model.id = uuid4()
        mock_model.nome = "Prefeitura Teste"
        mock_model.quota_tokens = 10000
        mock_model.tokens_consumidos = 5000
        mock_model.ativo = True
        mock_model.criado_em = datetime.utcnow()
        mock_model.atualizado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, Prefeitura)
        assert result.id.value == mock_model.id
        assert result.nome == mock_model.nome
        assert result.quota_tokens == mock_model.quota_tokens
        assert result.tokens_consumidos == mock_model.tokens_consumidos
        assert result.ativo == mock_model.ativo
