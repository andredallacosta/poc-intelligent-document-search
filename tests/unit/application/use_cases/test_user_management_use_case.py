from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from application.dto.auth_dto import ActivateUserDTO, CreateUserDTO, UserListDTO
from application.use_cases.user_management_use_case import UserManagementUseCase
from domain.entities.user import User
from domain.exceptions.auth_exceptions import EmailDeliveryError, UserNotFoundError
from domain.repositories.user_repository import UserRepository
from domain.services.authentication_service import AuthenticationService
from domain.services.email_service import EmailService
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole


class TestUserManagementUseCase:
    """Testes unitários para UserManagementUseCase"""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock do UserRepository"""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_auth_service(self):
        """Mock do AuthenticationService"""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def mock_email_service(self):
        """Mock do EmailService"""
        return Mock(spec=EmailService)

    @pytest.fixture
    def user_management_use_case(
        self, mock_user_repo, mock_auth_service, mock_email_service
    ):
        """Instância do UserManagementUseCase para testes"""
        return UserManagementUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            email_service=mock_email_service,
        )

    @pytest.fixture
    def admin_user(self):
        """Usuário admin para testes"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            id=UserId(uuid4()),
            email="admin@test.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def invited_user(self):
        """Usuário com convite pendente para testes"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            email="invited@test.com",
            full_name="Invited User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            is_active=False,
            email_verified=False,
            invitation_token="invitation_token_123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by=UserId(uuid4()),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            password_hash="temp_hash",
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_user_with_invitation_success(
        self,
        user_management_use_case,
        mock_user_repo,
        mock_auth_service,
        mock_email_service,
        admin_user,
    ):
        """Deve criar usuário com convite com sucesso"""
        # Arrange
        request = CreateUserDTO(
            email="newuser@test.com",
            full_name="New User",
            role="user",
            primary_municipality_id=admin_user.primary_municipality_id.value,
        )
        mock_user_repo.find_by_email = AsyncMock(return_value=None)
        mock_user_repo.find_by_id = AsyncMock(return_value=admin_user)
        mock_user_repo.save = AsyncMock()
        mock_email_service.send_invitation_email = AsyncMock()
        # Act
        result = await user_management_use_case.create_user_with_invitation(
            request, admin_user
        )
        # Assert
        assert isinstance(result, UserListDTO)
        assert result.email == "newuser@test.com"
        assert result.full_name == "New User"
        assert result.role == "user"
        assert result.is_active is False
        assert result.email_verified is False
        assert result.invited_by_name == admin_user.full_name
        # Verifica chamadas
        mock_user_repo.find_by_email.assert_called_once_with("newuser@test.com")
        mock_user_repo.find_by_id.assert_called_once_with(admin_user.id)
        mock_user_repo.save.assert_called_once()
        mock_email_service.send_invitation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_with_invitation_email_exists(
        self, user_management_use_case, mock_user_repo, admin_user
    ):
        """Deve falhar se email já existe"""
        # Arrange
        request = CreateUserDTO(
            email="existing@test.com",
            full_name="Existing User",
            role="user",
            primary_municipality_id=admin_user.primary_municipality_id.value,
        )
        existing_user = User(
            email="existing@test.com", full_name="Existing User", password_hash="hash"
        )
        mock_user_repo.find_by_email = AsyncMock(return_value=existing_user)
        # Act & Assert
        with pytest.raises(ValueError, match="Email já cadastrado no sistema"):
            await user_management_use_case.create_user_with_invitation(
                request, admin_user
            )

    @pytest.mark.asyncio
    async def test_activate_user_account_email_password_success(
        self,
        user_management_use_case,
        mock_user_repo,
        mock_auth_service,
        mock_email_service,
        invited_user,
    ):
        """Deve ativar conta com email/senha com sucesso"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="email_password",
            password="new_password123",
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_user_repo.save = AsyncMock()
        mock_auth_service.hash_password = Mock(return_value="hashed_new_password")
        mock_email_service.send_welcome_email = AsyncMock()
        mock_email_service.send_account_activated_email = AsyncMock()
        # Act
        result = await user_management_use_case.activate_user_account(request)
        # Assert
        assert isinstance(result, UserListDTO)
        assert result.email == invited_user.email
        assert result.is_active is True
        assert result.email_verified is True
        # Verifica que o usuário foi ativado corretamente
        assert invited_user.is_active is True
        assert invited_user.auth_provider == AuthProvider.EMAIL_PASSWORD
        assert invited_user.password_hash == "hashed_new_password"
        assert invited_user.invitation_token is None
        # Verifica chamadas
        mock_auth_service.hash_password.assert_called_once_with("new_password123")
        mock_user_repo.save.assert_called_once_with(invited_user)
        mock_email_service.send_welcome_email.assert_called_once()
        mock_email_service.send_account_activated_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_account_google_oauth2_success(
        self,
        user_management_use_case,
        mock_user_repo,
        mock_auth_service,
        mock_email_service,
        invited_user,
    ):
        """Deve ativar conta com Google OAuth2 com sucesso"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="google_oauth2",
            google_token="google_token_123",
        )
        google_user_info = {
            "sub": "google_user_123456",
            "email": invited_user.email,
            "name": invited_user.full_name,
        }
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_user_repo.save = AsyncMock()
        mock_auth_service._verify_google_token = AsyncMock(
            return_value=google_user_info
        )
        mock_email_service.send_welcome_email = AsyncMock()
        mock_email_service.send_account_activated_email = AsyncMock()
        # Act
        result = await user_management_use_case.activate_user_account(request)
        # Assert
        assert isinstance(result, UserListDTO)
        assert result.email == invited_user.email
        assert result.is_active is True
        assert result.email_verified is True
        # Verifica que o usuário foi ativado corretamente
        assert invited_user.is_active is True
        assert invited_user.auth_provider == AuthProvider.GOOGLE_OAUTH2
        assert invited_user.google_id == "google_user_123456"
        assert invited_user.password_hash is None
        assert invited_user.invitation_token is None
        # Verifica chamadas
        mock_auth_service._verify_google_token.assert_called_once_with(
            "google_token_123"
        )
        mock_user_repo.save.assert_called_once_with(invited_user)
        mock_email_service.send_welcome_email.assert_called_once()
        mock_email_service.send_account_activated_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_account_invalid_token(
        self, user_management_use_case, mock_user_repo
    ):
        """Deve falhar com token de convite inválido"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invalid_token",
            auth_provider="email_password",
            password="password123",
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=None)
        # Act & Assert
        with pytest.raises(UserNotFoundError, match="Token de convite inválido"):
            await user_management_use_case.activate_user_account(request)

    @pytest.mark.asyncio
    async def test_activate_user_account_email_password_no_password(
        self, user_management_use_case, mock_user_repo, invited_user
    ):
        """Deve falhar se escolher email/senha mas não fornecer senha"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="email_password",
            password=None,
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        # Act & Assert
        with pytest.raises(
            ValueError, match="Senha obrigatória para ativação com email/senha"
        ):
            await user_management_use_case.activate_user_account(request)

    @pytest.mark.asyncio
    async def test_activate_user_account_google_oauth2_no_token(
        self, user_management_use_case, mock_user_repo, invited_user
    ):
        """Deve falhar se escolher Google OAuth2 mas não fornecer token"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="google_oauth2",
            google_token=None,
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        # Act & Assert
        with pytest.raises(
            ValueError, match="Token Google obrigatório para ativação com Google OAuth2"
        ):
            await user_management_use_case.activate_user_account(request)

    @pytest.mark.asyncio
    async def test_activate_user_account_google_email_mismatch(
        self, user_management_use_case, mock_user_repo, mock_auth_service, invited_user
    ):
        """Deve falhar se email do token Google não confere com o convite"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="google_oauth2",
            google_token="google_token_123",
        )
        google_user_info = {
            "sub": "google_user_123456",
            "email": "different@email.com",  # Email diferente
            "name": "Different User",
        }
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_auth_service._verify_google_token = AsyncMock(
            return_value=google_user_info
        )
        # Act & Assert
        with pytest.raises(
            ValueError, match="Email do token Google não confere com o email do convite"
        ):
            await user_management_use_case.activate_user_account(request)

    @pytest.mark.asyncio
    async def test_activate_user_account_invalid_google_token(
        self, user_management_use_case, mock_user_repo, mock_auth_service, invited_user
    ):
        """Deve falhar com token Google inválido"""
        # Arrange
        request = ActivateUserDTO(
            invitation_token="invitation_token_123",
            auth_provider="google_oauth2",
            google_token="invalid_google_token",
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_auth_service._verify_google_token = AsyncMock(
            side_effect=Exception("Invalid token")
        )
        # Act & Assert
        with pytest.raises(ValueError, match="Token Google inválido"):
            await user_management_use_case.activate_user_account(request)

    @pytest.mark.asyncio
    async def test_list_users_by_municipality_success(
        self, user_management_use_case, mock_user_repo, admin_user
    ):
        """Deve listar usuários por prefeitura com sucesso"""
        # Arrange
        users = [admin_user]
        mock_user_repo.find_by_municipality_id = AsyncMock(return_value=users)
        municipality_id = admin_user.primary_municipality_id.value
        # Act
        result = await user_management_use_case.list_users_by_municipality(
            municipality_id, admin_user
        )
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], UserListDTO)
        assert result[0].email == admin_user.email
        assert result[0].full_name == admin_user.full_name

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self, user_management_use_case, mock_user_repo, admin_user
    ):
        """Deve desativar usuário com sucesso"""
        # Arrange
        str(admin_user.id.value)
        mock_user_repo.find_by_id = AsyncMock(return_value=admin_user)
        mock_user_repo.save = AsyncMock()
        # Criar outro usuário para desativar (não pode desativar a si mesmo)
        other_user = User(
            id=UserId(uuid4()),
            email="other@test.com",
            full_name="Other User",
            role=UserRole.USER,
            primary_municipality_id=admin_user.primary_municipality_id,
            municipality_ids=[admin_user.primary_municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
        )
        mock_user_repo.find_by_id = AsyncMock(return_value=other_user)
        # Act
        result = await user_management_use_case.deactivate_user(
            other_user.id.value, admin_user
        )
        # Assert
        assert isinstance(result, UserListDTO)
        assert result.is_active is False
        assert other_user.is_active is False
        mock_user_repo.find_by_id.assert_called_once_with(UserId(other_user.id.value))
        mock_user_repo.save.assert_called_once_with(other_user)

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(
        self, user_management_use_case, mock_user_repo, admin_user
    ):
        """Deve falhar se usuário não encontrado"""
        # Arrange
        str(uuid4())
        # user_id já definido acima
        mock_user_repo.find_by_id = AsyncMock(return_value=None)
        # Act & Assert
        with pytest.raises(UserNotFoundError, match="Usuário não encontrado"):
            await user_management_use_case.deactivate_user(uuid4(), admin_user)

    @pytest.mark.asyncio
    async def test_email_delivery_error_handling(
        self,
        user_management_use_case,
        mock_user_repo,
        mock_auth_service,
        mock_email_service,
        admin_user,
    ):
        """Deve tratar erros de entrega de email"""
        # Arrange
        request = CreateUserDTO(
            email="newuser@test.com",
            full_name="New User",
            role="user",
            primary_municipality_id=admin_user.primary_municipality_id.value,
        )
        mock_user_repo.find_by_email = AsyncMock(return_value=None)
        mock_user_repo.find_by_id = AsyncMock(return_value=admin_user)
        mock_user_repo.save = AsyncMock()
        mock_email_service.send_invitation_email = AsyncMock(
            side_effect=EmailDeliveryError("Falha no envio de email")
        )
        # Act & Assert
        with pytest.raises(EmailDeliveryError, match="Falha no envio de email"):
            await user_management_use_case.create_user_with_invitation(
                request, admin_user
            )
