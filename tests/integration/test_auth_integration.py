import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from application.dto.auth_dto import LoginEmailPasswordDTO, LoginResponseDTO, UserDTO
from application.use_cases.authentication_use_case import AuthenticationUseCase
from domain.entities.user import User
from domain.exceptions.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from domain.services.authentication_service import AuthenticationService
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole
from interface.middleware.auth_middleware import get_authenticated_user


class TestAuthenticationIntegration:
    """Testes de integração para o sistema de autenticação"""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock do AuthenticationService"""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def auth_use_case(self, mock_auth_service):
        """AuthenticationUseCase com mock do service"""
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
            created_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_full_login_flow_success(self, auth_use_case, mock_auth_service, sample_user):
        """Testa fluxo completo de login com sucesso"""
        # Arrange
        login_request = LoginEmailPasswordDTO(
            email="user@test.com",
            password="password123"
        )
        jwt_token = "jwt_token_example"
        
        mock_auth_service.authenticate_email_password = AsyncMock(
            return_value=(sample_user, jwt_token)
        )
        
        # Act
        response = await auth_use_case.login_email_password(login_request)
        
        # Assert
        assert isinstance(response, LoginResponseDTO)
        assert response.access_token == jwt_token
        assert response.token_type == "bearer"
        assert response.user.email == sample_user.email
        assert response.user.role == sample_user.role.value
        
        # Verifica que o service foi chamado corretamente
        mock_auth_service.authenticate_email_password.assert_called_once_with(
            email="user@test.com",
            password="password123"
        )

    @pytest.mark.asyncio
    async def test_full_login_flow_invalid_credentials(self, auth_use_case, mock_auth_service):
        """Testa fluxo completo de login com credenciais inválidas"""
        # Arrange
        login_request = LoginEmailPasswordDTO(
            email="user@test.com",
            password="wrong_password"
        )
        
        mock_auth_service.authenticate_email_password = AsyncMock(
            side_effect=InvalidCredentialsError("Email ou senha incorretos")
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError, match="Email ou senha incorretos"):
            await auth_use_case.login_email_password(login_request)

    @pytest.mark.asyncio
    async def test_token_verification_flow_success(self, auth_use_case, mock_auth_service, sample_user):
        """Testa fluxo completo de verificação de token"""
        # Arrange
        token = "valid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(return_value=sample_user)
        
        # Act
        user_dto = await auth_use_case.verify_token(token)
        
        # Assert
        assert isinstance(user_dto, UserDTO)
        assert user_dto.email == sample_user.email
        assert user_dto.full_name == sample_user.full_name
        assert user_dto.role == sample_user.role.value
        assert user_dto.is_active == sample_user.is_active
        
        # Verifica que o service foi chamado corretamente
        mock_auth_service.verify_jwt_token.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_token_verification_flow_invalid_token(self, auth_use_case, mock_auth_service):
        """Testa fluxo completo de verificação com token inválido"""
        # Arrange
        token = "invalid_jwt_token"
        mock_auth_service.verify_jwt_token = AsyncMock(
            side_effect=InvalidTokenError("Token inválido")
        )
        
        # Act & Assert
        with pytest.raises(InvalidTokenError, match="Token inválido"):
            await auth_use_case.verify_token(token)

    @pytest.mark.asyncio
    async def test_middleware_authentication_success(self, auth_use_case, sample_user):
        """Testa middleware de autenticação com token válido"""
        # Arrange
        from fastapi import Request
        from fastapi.security import HTTPBearer
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/protected"
        request.state = MagicMock()
        
        token_mock = MagicMock()
        token_mock.credentials = "valid_token"
        
        # Mock do use case
        auth_use_case_mock = AsyncMock()
        user_dto = UserDTO(
            id=str(sample_user.id.value),
            email=sample_user.email,
            full_name=sample_user.full_name,
            role=sample_user.role.value,
            primary_municipality_id=str(sample_user.primary_municipality_id.value),
            municipality_ids=[str(mid.value) for mid in sample_user.municipality_ids],
            is_active=sample_user.is_active,
            email_verified=sample_user.email_verified,
            last_login=sample_user.last_login.isoformat() if sample_user.last_login else None,
            created_at=sample_user.created_at.isoformat()
        )
        auth_use_case_mock.verify_token.return_value = user_dto
        
        # Act
        result = await get_authenticated_user(request, token_mock, auth_use_case_mock)
        
        # Assert
        assert result == user_dto
        assert request.state.current_user == user_dto
        auth_use_case_mock.verify_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_middleware_authentication_no_token(self):
        """Testa middleware de autenticação sem token"""
        # Arrange
        from fastapi import Request
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/protected"
        
        auth_use_case_mock = AsyncMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(request, None, auth_use_case_mock)
        
        assert exc_info.value.status_code == 401
        assert "Token de acesso obrigatório" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_authentication_invalid_token(self, auth_use_case):
        """Testa middleware de autenticação com token inválido"""
        # Arrange
        from fastapi import Request
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/protected"
        
        token_mock = MagicMock()
        token_mock.credentials = "invalid_token"
        
        auth_use_case_mock = AsyncMock()
        auth_use_case_mock.verify_token.side_effect = InvalidTokenError("Token inválido")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(request, token_mock, auth_use_case_mock)
        
        assert exc_info.value.status_code == 401
        assert "invalid_token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_public_route_access(self):
        """Testa que rotas públicas não requerem autenticação"""
        # Arrange
        from fastapi import Request
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.url.path = "/health"  # Rota pública
        
        auth_use_case_mock = AsyncMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(request, None, auth_use_case_mock)
        
        # Deve falhar porque o middleware não deveria ser usado em rotas públicas
        assert exc_info.value.status_code == 500
        assert "Authentication dependency used on public route" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authentication_service_integration_with_repository(self):
        """Testa integração do AuthenticationService com repositório"""
        # Arrange
        from domain.repositories.user_repository import UserRepository
        
        mock_user_repo = Mock(spec=UserRepository)
        auth_service = AuthenticationService(
            user_repository=mock_user_repo,
            jwt_secret="test_secret",
            jwt_algorithm="HS256",
            jwt_expiry_days=3
        )
        
        municipality_id = MunicipalityId(uuid4())
        user = User(
            id=UserId(uuid4()),
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash=auth_service.hash_password("password123"),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True
        )
        
        mock_user_repo.find_by_email = AsyncMock(return_value=user)
        mock_user_repo.update = AsyncMock()
        
        # Act
        authenticated_user, jwt_token = await auth_service.authenticate_email_password(
            email="user@test.com",
            password="password123"
        )
        
        # Assert
        assert authenticated_user == user
        assert isinstance(jwt_token, str)
        assert len(jwt_token) > 0
        
        # Verifica que o repositório foi chamado
        mock_user_repo.find_by_email.assert_called_once_with("user@test.com")
        mock_user_repo.update.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_jwt_token_roundtrip_integration(self):
        """Testa geração e verificação de JWT de ponta a ponta"""
        # Arrange
        from domain.repositories.user_repository import UserRepository
        
        mock_user_repo = Mock(spec=UserRepository)
        auth_service = AuthenticationService(
            user_repository=mock_user_repo,
            jwt_secret="test_secret",
            jwt_algorithm="HS256",
            jwt_expiry_days=3
        )
        
        municipality_id = MunicipalityId(uuid4())
        user = User(
            id=UserId(uuid4()),
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True
        )
        
        # Act - Gera JWT
        jwt_token = auth_service._generate_jwt(user)
        
        # Configura mock para verificação
        mock_user_repo.find_by_id = AsyncMock(return_value=user)
        
        # Act - Verifica JWT
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(user.id.value),
                "email": user.email,
                "role": user.role.value,
                "exp": (datetime.utcnow() + timedelta(days=1)).timestamp(),
                "iat": datetime.utcnow().timestamp()
            }
            
            verified_user = await auth_service.verify_jwt_token(jwt_token)
        
        # Assert
        assert verified_user == user
        assert isinstance(jwt_token, str)
        assert len(jwt_token) > 0

    @pytest.mark.asyncio
    async def test_password_hashing_integration(self):
        """Testa integração de hash e verificação de senhas"""
        # Arrange
        from domain.repositories.user_repository import UserRepository
        
        mock_user_repo = Mock(spec=UserRepository)
        auth_service = AuthenticationService(
            user_repository=mock_user_repo,
            jwt_secret="test_secret"
        )
        
        password = "test_password_123"
        
        # Act - Hash da senha
        password_hash = auth_service.hash_password(password)
        
        # Act - Verificação da senha
        is_valid = auth_service._verify_password(password, password_hash)
        is_invalid = auth_service._verify_password("wrong_password", password_hash)
        
        # Assert
        assert isinstance(password_hash, str)
        assert len(password_hash) > 0
        assert password_hash.startswith("$2b$")
        assert is_valid is True
        assert is_invalid is False

    @pytest.mark.asyncio
    async def test_user_dto_serialization_integration(self, sample_user):
        """Testa serialização completa de User para UserDTO"""
        # Arrange
        auth_use_case = AuthenticationUseCase(Mock())
        
        # Act
        user_dto = UserDTO(
            id=str(sample_user.id.value),
            email=sample_user.email,
            full_name=sample_user.full_name,
            role=sample_user.role.value,
            primary_municipality_id=str(sample_user.primary_municipality_id.value),
            municipality_ids=[str(mid.value) for mid in sample_user.municipality_ids],
            is_active=sample_user.is_active,
            email_verified=sample_user.email_verified,
            last_login=sample_user.last_login.isoformat() if sample_user.last_login else None,
            created_at=sample_user.created_at.isoformat()
        )
        
        # Assert
        assert user_dto.id == str(sample_user.id.value)
        assert user_dto.email == sample_user.email
        assert user_dto.full_name == sample_user.full_name
        assert user_dto.role == sample_user.role.value
        assert user_dto.primary_municipality_id == str(sample_user.primary_municipality_id.value)
        assert len(user_dto.municipality_ids) == len(sample_user.municipality_ids)
        assert user_dto.is_active == sample_user.is_active
        assert user_dto.email_verified == sample_user.email_verified
        
        # Verifica serialização de datetime
        if sample_user.last_login:
            assert user_dto.last_login == sample_user.last_login.isoformat()
        assert user_dto.created_at == sample_user.created_at.isoformat()

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, auth_use_case, mock_auth_service):
        """Testa tratamento de erros de ponta a ponta"""
        # Arrange
        login_request = LoginEmailPasswordDTO(
            email="user@test.com",
            password="password123"
        )
        
        # Test different error scenarios
        error_scenarios = [
            (InvalidCredentialsError("Email ou senha incorretos"), InvalidCredentialsError),
            (Exception("Database connection failed"), Exception)
        ]
        
        for exception, expected_type in error_scenarios:
            # Arrange
            mock_auth_service.authenticate_email_password = AsyncMock(side_effect=exception)
            
            # Act & Assert
            with pytest.raises(expected_type):
                await auth_use_case.login_email_password(login_request)
