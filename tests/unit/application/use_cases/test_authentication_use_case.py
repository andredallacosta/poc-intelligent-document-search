from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from application.dto.auth_dto import (
    LoginEmailPasswordDTO,
    LoginGoogleOAuth2DTO,
    LoginResponseDTO,
    UserDTO,
)
from application.use_cases.authentication_use_case import AuthenticationUseCase
from domain.entities.user import User
from domain.exceptions.auth_exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from domain.services.authentication_service import AuthenticationService
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole


class TestAuthenticationUseCase:
    """Testes unitários para AuthenticationUseCase"""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock do AuthenticationService"""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def auth_use_case(self, mock_auth_service):
        """Instância do AuthenticationUseCase para testes"""
        return AuthenticationUseCase(auth_service=mock_auth_service)

    @pytest.fixture
    def sample_user(self):
        """Usuário de exemplo para testes"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            id=UserId(uuid4()),
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True,
            last_login=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def google_user(self):
        """Usuário Google OAuth2 para testes"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            id=UserId(uuid4()),
            email="user@gmail.com",
            full_name="Google User",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            auth_provider=AuthProvider.GOOGLE_OAUTH2,
            google_id="google_123456",
            is_active=True,
            email_verified=True,
            last_login=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_login_email_password_success(
        self, auth_use_case, mock_auth_service, sample_user
    ):
        """Deve fazer login com email/senha com sucesso"""
        # Arrange
        request = LoginEmailPasswordDTO(email="user@test.com", password="password123")
        jwt_token = "jwt_token_example"
        mock_auth_service.authenticate_email_password = AsyncMock(
            return_value=(sample_user, jwt_token)
        )
        # Act
        response = await auth_use_case.login_email_password(request)
        # Assert
        assert isinstance(response, LoginResponseDTO)
        assert response.access_token == jwt_token
        assert response.token_type == "bearer"
        assert response.user.email == sample_user.email
        assert response.user.full_name == sample_user.full_name
        assert response.user.role == sample_user.role.value
        assert response.user.is_active == sample_user.is_active
        mock_auth_service.authenticate_email_password.assert_called_once_with(
            email="user@test.com", password="password123"
        )

    @pytest.mark.asyncio
    async def test_login_email_password_invalid_credentials(
        self, auth_use_case, mock_auth_service
    ):
        """Deve falhar com credenciais inválidas"""
        # Arrange
        request = LoginEmailPasswordDTO(
            email="user@test.com", password="wrong_password"
        )
        mock_auth_service.authenticate_email_password = AsyncMock(
            side_effect=InvalidCredentialsError("Email ou senha incorretos")
        )
        # Act & Assert
        with pytest.raises(InvalidCredentialsError):
            await auth_use_case.login_email_password(request)

    @pytest.mark.asyncio
    async def test_login_email_password_user_not_found(
        self, auth_use_case, mock_auth_service
    ):
        """Deve falhar se usuário não encontrado"""
        # Arrange
        request = LoginEmailPasswordDTO(
            email="nonexistent@test.com", password="password123"
        )
        mock_auth_service.authenticate_email_password = AsyncMock(
            side_effect=UserNotFoundError("Usuário não encontrado")
        )
        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await auth_use_case.login_email_password(request)

    @pytest.mark.asyncio
    async def test_login_google_oauth2_success(
        self, auth_use_case, mock_auth_service, google_user
    ):
        """Deve fazer login com Google OAuth2 com sucesso"""
        # Arrange
        request = LoginGoogleOAuth2DTO(google_token="google_token_example")
        jwt_token = "jwt_token_example"
        mock_auth_service.authenticate_google_oauth2 = AsyncMock(
            return_value=(google_user, jwt_token)
        )
        # Act
        response = await auth_use_case.login_google_oauth2(request)
        # Assert
        assert isinstance(response, LoginResponseDTO)
        assert response.access_token == jwt_token
        assert response.token_type == "bearer"
        assert response.user.email == google_user.email
        assert response.user.full_name == google_user.full_name
        assert response.user.role == google_user.role.value
        assert response.user.is_active == google_user.is_active
        mock_auth_service.authenticate_google_oauth2.assert_called_once_with(
            google_token="google_token_example"
        )

    @pytest.mark.asyncio
    async def test_login_google_oauth2_user_not_found(
        self, auth_use_case, mock_auth_service
    ):
        """Deve falhar se usuário Google não encontrado"""
        # Arrange
        request = LoginGoogleOAuth2DTO(google_token="google_token_example")
        mock_auth_service.authenticate_google_oauth2 = AsyncMock(
            side_effect=UserNotFoundError(
                "Usuário não encontrado. Solicite convite ao administrador."
            )
        )
        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await auth_use_case.login_google_oauth2(request)

    @pytest.mark.asyncio
    async def test_verify_token_success(
        self, auth_use_case, mock_auth_service, sample_user
    ):
        """Deve verificar token com sucesso"""
        # Arrange
        token = "valid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(return_value=sample_user)
        # Act
        user_dto = await auth_use_case.verify_token(token)
        # Assert
        assert isinstance(user_dto, UserDTO)
        assert user_dto.id == str(sample_user.id.value)
        assert user_dto.email == sample_user.email
        assert user_dto.full_name == sample_user.full_name
        assert user_dto.role == sample_user.role.value
        assert user_dto.primary_municipality_id == str(
            sample_user.primary_municipality_id.value
        )
        assert user_dto.municipality_ids == [
            str(mid.value) for mid in sample_user.municipality_ids
        ]
        assert user_dto.is_active == sample_user.is_active
        assert user_dto.email_verified == sample_user.email_verified
        assert user_dto.last_login == sample_user.last_login.isoformat()
        assert user_dto.created_at == sample_user.created_at.isoformat()
        mock_auth_service.verify_jwt_token.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_verify_token_invalid_token(self, auth_use_case, mock_auth_service):
        """Deve falhar com token inválido"""
        # Arrange
        token = "invalid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(
            side_effect=InvalidTokenError("Token inválido")
        )
        # Act & Assert
        with pytest.raises(InvalidTokenError):
            await auth_use_case.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_user_without_municipality(
        self, auth_use_case, mock_auth_service
    ):
        """Deve verificar token para usuário sem prefeitura"""
        # Arrange
        user_without_municipality = User(
            id=UserId(uuid4()),
            email="superuser@test.com",
            full_name="Super User",
            role=UserRole.SUPERUSER,
            primary_municipality_id=None,
            municipality_ids=[],
            password_hash="hashed_password",
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
        )
        token = "valid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(
            return_value=user_without_municipality
        )
        # Act
        user_dto = await auth_use_case.verify_token(token)
        # Assert
        assert user_dto.primary_municipality_id is None
        assert user_dto.municipality_ids == []
        assert user_dto.last_login is None

    @pytest.mark.asyncio
    async def test_verify_token_user_without_last_login(
        self, auth_use_case, mock_auth_service
    ):
        """Deve verificar token para usuário sem último login"""
        # Arrange
        municipality_id = MunicipalityId(uuid4())
        user_no_login = User(
            id=UserId(uuid4()),
            email="newuser@test.com",
            full_name="New User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            is_active=True,
            email_verified=False,
            last_login=None,  # Sem último login
            created_at=datetime.utcnow(),
        )
        token = "valid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(return_value=user_no_login)
        # Act
        user_dto = await auth_use_case.verify_token(token)
        # Assert
        assert user_dto.last_login is None
        assert user_dto.email_verified is False

    def test_create_login_response_structure(self, auth_use_case, sample_user):
        """Deve criar resposta de login com estrutura correta"""
        # Arrange
        jwt_token = "test_jwt_token"
        # Act
        response = auth_use_case._create_login_response(sample_user, jwt_token)
        # Assert
        assert isinstance(response, LoginResponseDTO)
        assert response.access_token == jwt_token
        assert response.token_type == "bearer"
        # Verifica UserDTO
        user_dto = response.user
        assert isinstance(user_dto, UserDTO)
        assert user_dto.id == str(sample_user.id.value)
        assert user_dto.email == sample_user.email
        assert user_dto.full_name == sample_user.full_name
        assert user_dto.role == sample_user.role.value
        assert user_dto.is_active == sample_user.is_active
        assert user_dto.email_verified == sample_user.email_verified

    def test_create_login_response_with_multiple_municipalities(self, auth_use_case):
        """Deve criar resposta para usuário com múltiplas prefeituras"""
        # Arrange
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        admin_user = User(
            id=UserId(uuid4()),
            email="admin@test.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_1,
            municipality_ids=[municipality_1, municipality_2],
            password_hash="hashed_password",
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
        )
        jwt_token = "test_jwt_token"
        # Act
        response = auth_use_case._create_login_response(admin_user, jwt_token)
        # Assert
        assert len(response.user.municipality_ids) == 2
        assert str(municipality_1.value) in response.user.municipality_ids
        assert str(municipality_2.value) in response.user.municipality_ids
        assert response.user.primary_municipality_id == str(municipality_1.value)

    def test_create_login_response_superuser_no_municipality(self, auth_use_case):
        """Deve criar resposta para superuser sem prefeitura"""
        # Arrange
        superuser = User(
            id=UserId(uuid4()),
            email="superuser@test.com",
            full_name="Super User",
            role=UserRole.SUPERUSER,
            primary_municipality_id=None,
            municipality_ids=[],
            password_hash="hashed_password",
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
        )
        jwt_token = "test_jwt_token"
        # Act
        response = auth_use_case._create_login_response(superuser, jwt_token)
        # Assert
        assert response.user.primary_municipality_id is None
        assert response.user.municipality_ids == []
        assert response.user.role == "superuser"

    @pytest.mark.asyncio
    async def test_login_email_password_dto_validation(
        self, auth_use_case, mock_auth_service, sample_user
    ):
        """Deve validar DTO de login email/senha"""
        # Arrange
        request = LoginEmailPasswordDTO(email="user@test.com", password="password123")
        jwt_token = "jwt_token_example"
        mock_auth_service.authenticate_email_password = AsyncMock(
            return_value=(sample_user, jwt_token)
        )
        # Act
        response = await auth_use_case.login_email_password(request)
        # Assert
        # Verifica que o DTO foi usado corretamente
        mock_auth_service.authenticate_email_password.assert_called_once_with(
            email=request.email, password=request.password
        )
        assert response.access_token == jwt_token

    @pytest.mark.asyncio
    async def test_login_google_oauth2_dto_validation(
        self, auth_use_case, mock_auth_service, google_user
    ):
        """Deve validar DTO de login Google OAuth2"""
        # Arrange
        request = LoginGoogleOAuth2DTO(google_token="google_token_example")
        jwt_token = "jwt_token_example"
        mock_auth_service.authenticate_google_oauth2 = AsyncMock(
            return_value=(google_user, jwt_token)
        )
        # Act
        response = await auth_use_case.login_google_oauth2(request)
        # Assert
        # Verifica que o DTO foi usado corretamente
        mock_auth_service.authenticate_google_oauth2.assert_called_once_with(
            google_token=request.google_token
        )
        assert response.access_token == jwt_token

    @pytest.mark.asyncio
    async def test_user_dto_serialization_comprehensive(
        self, auth_use_case, mock_auth_service
    ):
        """Deve serializar UserDTO corretamente em todos os cenários"""
        # Arrange - Usuário com todos os campos preenchidos
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        complete_user = User(
            id=UserId(uuid4()),
            email="complete@test.com",
            full_name="Complete User",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_1,
            municipality_ids=[municipality_1, municipality_2],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True,
            last_login=datetime(2023, 10, 8, 10, 30, 0),
            created_at=datetime(2023, 10, 1, 9, 0, 0),
        )
        token = "valid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(return_value=complete_user)
        # Act
        user_dto = await auth_use_case.verify_token(token)
        # Assert - Verifica todos os campos
        assert user_dto.id == str(complete_user.id.value)
        assert user_dto.email == "complete@test.com"
        assert user_dto.full_name == "Complete User"
        assert user_dto.role == "admin"
        assert user_dto.primary_municipality_id == str(municipality_1.value)
        assert len(user_dto.municipality_ids) == 2
        assert str(municipality_1.value) in user_dto.municipality_ids
        assert str(municipality_2.value) in user_dto.municipality_ids
        assert user_dto.is_active is True
        assert user_dto.email_verified is True
        assert user_dto.last_login == "2023-10-08T10:30:00"
        assert user_dto.created_at == "2023-10-01T09:00:00"
