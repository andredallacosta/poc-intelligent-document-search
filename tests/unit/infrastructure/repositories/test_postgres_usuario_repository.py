import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.usuario import Usuario
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.value_objects.usuario_id import UsuarioId
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.database.models import UsuarioModel


class TestPostgresUsuarioRepository:
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        return PostgresUsuarioRepository(mock_session)
    
    @pytest.fixture
    def sample_usuario(self):
        return Usuario(
            id=UsuarioId.from_uuid(uuid4()),
            prefeitura_id=PrefeituraId.from_uuid(uuid4()),
            nome="João Silva",
            email="joao@teste.com",
            senha_hash="hashed_password",
            ativo=True,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow()
        )

    def test_init(self, mock_session):
        repo = PostgresUsuarioRepository(mock_session)
        assert repo._session == mock_session

    @pytest.mark.asyncio
    async def test_save_success(self, repository, mock_session, sample_usuario):
        mock_session.flush = AsyncMock()
        
        result = await repository.save(sample_usuario)
        
        assert result == sample_usuario
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_email_unique_constraint_error(self, repository, mock_session, sample_usuario):
        mock_session.flush.side_effect = IntegrityError("unique constraint email", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="já existe"):
            await repository.save(sample_usuario)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_other_integrity_error(self, repository, mock_session, sample_usuario):
        mock_session.flush.side_effect = IntegrityError("other error", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="Erro ao salvar usuário"):
            await repository.save(sample_usuario)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_found(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_by_id(sample_usuario.id)
        
        assert result == sample_usuario

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_id(UsuarioId.from_uuid(uuid4()))
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_email_found(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_by_email("joao@teste.com")
        
        assert result == sample_usuario

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_email("inexistente@teste.com")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_prefeitura_id_success(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_by_prefeitura_id(sample_usuario.prefeitura_id)
        
        assert len(result) == 1
        assert result[0] == sample_usuario

    @pytest.mark.asyncio
    async def test_find_by_prefeitura_id_empty(self, repository, mock_session):
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = await repository.find_by_prefeitura_id(PrefeituraId.from_uuid(uuid4()))
        
        assert result == []

    @pytest.mark.asyncio
    async def test_find_all_active_success(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_all_active()
        
        assert len(result) == 1
        assert result[0] == sample_usuario

    @pytest.mark.asyncio
    async def test_find_all_active_with_pagination(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_all_active(limit=10, offset=5)
        
        assert len(result) == 1
        assert result[0] == sample_usuario

    @pytest.mark.asyncio
    async def test_find_all_success(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_all()
        
        assert len(result) == 1
        assert result[0] == sample_usuario

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session, sample_usuario):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.update(sample_usuario)
        
        assert result == sample_usuario
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_session, sample_usuario):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(BusinessRuleViolationError, match="não encontrado"):
            await repository.update(sample_usuario)

    @pytest.mark.asyncio
    async def test_update_email_unique_constraint_error(self, repository, mock_session, sample_usuario):
        mock_session.execute.side_effect = IntegrityError("unique constraint email", "params", "orig")
        mock_session.rollback = AsyncMock()
        
        with pytest.raises(BusinessRuleViolationError, match="já existe"):
            await repository.update(sample_usuario)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(UsuarioId.from_uuid(uuid4()))
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.delete(UsuarioId.from_uuid(uuid4()))
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists(UsuarioId.from_uuid(uuid4()))
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists(UsuarioId.from_uuid(uuid4()))
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_email_true(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_email("teste@email.com")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_email_false(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await repository.exists_by_email("inexistente@email.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_count_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result
        
        result = await repository.count()
        
        assert result == 15

    @pytest.mark.asyncio
    async def test_count_active_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 12
        mock_session.execute.return_value = mock_result
        
        result = await repository.count_active()
        
        assert result == 12

    @pytest.mark.asyncio
    async def test_count_by_prefeitura_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        result = await repository.count_by_prefeitura(PrefeituraId.from_uuid(uuid4()))
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_find_anonimos_success(self, repository, mock_session, sample_usuario):
        mock_model = Mock(spec=UsuarioModel)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_model]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, '_model_to_entity', return_value=sample_usuario):
            result = await repository.find_anonimos()
        
        assert len(result) == 1
        assert result[0] == sample_usuario

    @pytest.mark.asyncio
    async def test_count_anonimos_success(self, repository, mock_session):
        mock_result = Mock()
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result
        
        result = await repository.count_anonimos()
        
        assert result == 2

    def test_model_to_entity(self, repository):
        mock_model = Mock(spec=UsuarioModel)
        mock_model.id = uuid4()
        mock_model.prefeitura_id = uuid4()
        mock_model.nome = "João Silva"
        mock_model.email = "joao@teste.com"
        mock_model.senha_hash = "hashed_password"
        mock_model.ativo = True
        mock_model.criado_em = datetime.utcnow()
        mock_model.atualizado_em = datetime.utcnow()
        
        result = repository._model_to_entity(mock_model)
        
        assert isinstance(result, Usuario)
        assert result.id.value == mock_model.id
        assert result.prefeitura_id.value == mock_model.prefeitura_id
        assert result.nome == mock_model.nome
        assert result.email == mock_model.email
        assert result.senha_hash == mock_model.senha_hash
        assert result.ativo == mock_model.ativo
