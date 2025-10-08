import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import jwt

from domain.entities.user import User
from domain.exceptions.auth_exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserInactiveError,
    UserNotFoundError
)
from domain.repositories.user_repository import UserRepository
from domain.services.authentication_service import AuthenticationService
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole


class TestAuthenticationService:
    """Testes unitários para AuthenticationService"""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock do repositório de usuários"""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def auth_service(self, mock_user_repository):
        """Instância do AuthenticationService para testes"""
        return AuthenticationService(
            user_repository=mock_user_repository,
            jwt_secret="test_secret_key",
            jwt_algorithm="HS256",
            jwt_expiry_days=3,
            google_client_id="test_google_client_id"
        )

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
            password_hash="$2b$12$hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True
        )

    @pytest.fixture
    def google_user(self):
        """Usuário Google OAuth2 para testes"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            id=UserId(uuid4()),
            email="user@gmail.com",
            full_name="Google User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            auth_provider=AuthProvider.GOOGLE_OAUTH2,
            google_id="google_123456",
            is_active=True,
            email_verified=True
        )

    @pytest.mark.asyncio
    async def test_authenticate_email_password_success(self, auth_service, mock_user_repository, sample_user):
        """Deve autenticar com email/senha com sucesso"""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_user_repository.update = AsyncMock()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            # Act
            user, token = await auth_service.authenticate_email_password("user@test.com", "password123")
            
            # Assert
            assert user == sample_user
            assert isinstance(token, str)
            assert len(token) > 0
            mock_user_repository.find_by_email.assert_called_once_with("user@test.com")
            mock_user_repository.update.assert_called_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_authenticate_email_password_user_not_found(self, auth_service, mock_user_repository):
        """Deve falhar se usuário não encontrado"""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match="Usuário não encontrado"):
            await auth_service.authenticate_email_password("user@test.com", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_email_password_user_inactive(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar se usuário inativo"""
        # Arrange
        sample_user.is_active = False
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        # Act & Assert
        with pytest.raises(UserInactiveError, match="Conta desativada"):
            await auth_service.authenticate_email_password("user@test.com", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_email_password_wrong_provider(self, auth_service, mock_user_repository, google_user):
        """Deve falhar se usuário usa Google OAuth2"""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=google_user)
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError, match="Use login com Google para esta conta"):
            await auth_service.authenticate_email_password("user@gmail.com", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_email_password_wrong_password(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar com senha incorreta"""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        with patch.object(auth_service, '_verify_password', return_value=False):
            # Act & Assert
            with pytest.raises(InvalidCredentialsError, match="Email ou senha incorretos"):
                await auth_service.authenticate_email_password("user@test.com", "wrong_password")

    @pytest.mark.asyncio
    async def test_authenticate_email_password_no_password_hash(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar se usuário não tem password hash"""
        # Arrange
        sample_user.password_hash = None
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError, match="Email ou senha incorretos"):
            await auth_service.authenticate_email_password("user@test.com", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_google_oauth2_success(self, auth_service, mock_user_repository, google_user):
        """Deve autenticar com Google OAuth2 com sucesso"""
        # Arrange
        mock_user_repository.find_by_google_id = AsyncMock(return_value=google_user)
        mock_user_repository.save = AsyncMock()
        
        google_token_info = {
            "sub": "google_123456",
            "email": "user@gmail.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch.object(auth_service, '_verify_google_token', return_value=google_token_info):
            # Act
            user, token = await auth_service.authenticate_google_oauth2("google_token")
            
            # Assert
            assert user == google_user
            assert isinstance(token, str)
            assert len(token) > 0
            mock_user_repository.find_by_google_id.assert_called_once_with("google_123456")
            mock_user_repository.save.assert_called_once_with(google_user)

    @pytest.mark.asyncio
    async def test_authenticate_google_oauth2_user_not_found(self, auth_service, mock_user_repository):
        """Deve falhar se usuário Google não encontrado"""
        # Arrange
        mock_user_repository.find_by_google_id = AsyncMock(return_value=None)
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        
        google_token_info = {
            "sub": "google_123456",
            "email": "user@gmail.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch.object(auth_service, '_verify_google_token', return_value=google_token_info):
            # Act & Assert
            with pytest.raises(UserNotFoundError, match="Usuário não encontrado. Solicite convite ao administrador."):
                await auth_service.authenticate_google_oauth2("google_token")

    @pytest.mark.asyncio
    async def test_authenticate_google_oauth2_wrong_provider_fallback(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar se usuário existe mas usa email/senha"""
        # Arrange
        mock_user_repository.find_by_google_id = AsyncMock(return_value=None)
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        google_token_info = {
            "sub": "google_123456",
            "email": "user@test.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch.object(auth_service, '_verify_google_token', return_value=google_token_info):
            # Act & Assert
            with pytest.raises(InvalidCredentialsError, match="Use login com email/senha para esta conta"):
                await auth_service.authenticate_google_oauth2("google_token")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_success(self, auth_service, mock_user_repository, sample_user):
        """Deve verificar JWT com sucesso"""
        # Arrange
        token = auth_service._generate_jwt(sample_user)
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        
        # Mock jwt.decode para evitar problemas de timestamp
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(sample_user.id.value),
                "email": sample_user.email,
                "role": sample_user.role.value,
                "exp": (datetime.utcnow() + timedelta(days=1)).timestamp(),
                "iat": datetime.utcnow().timestamp()
            }
            
            # Act
            verified_user = await auth_service.verify_jwt_token(token)
            
            # Assert
            assert verified_user == sample_user
            mock_user_repository.find_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid_token(self, auth_service, mock_user_repository):
        """Deve falhar com token inválido"""
        # Act & Assert
        with pytest.raises(InvalidTokenError, match="Token inválido"):
            await auth_service.verify_jwt_token("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_expired(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar com token expirado"""
        # Arrange
        token = "expired_token"
        
        # Mock jwt.decode para simular token expirado
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Token expirado"):
                await auth_service.verify_jwt_token(token)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_user_not_found(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar se usuário do token não existe mais"""
        # Arrange
        token = "valid_token"
        mock_user_repository.find_by_id = AsyncMock(return_value=None)
        
        # Mock jwt.decode para retornar payload válido
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(sample_user.id.value),
                "exp": (datetime.utcnow() + timedelta(days=1)).timestamp()
            }
            
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Usuário não encontrado"):
                await auth_service.verify_jwt_token(token)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_user_inactive(self, auth_service, mock_user_repository, sample_user):
        """Deve falhar se usuário do token está inativo"""
        # Arrange
        token = "valid_token"
        sample_user.is_active = False
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        
        # Mock jwt.decode para retornar payload válido
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(sample_user.id.value),
                "exp": (datetime.utcnow() + timedelta(days=1)).timestamp()
            }
            
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Conta desativada"):
                await auth_service.verify_jwt_token(token)

    def test_generate_jwt_structure(self, auth_service, sample_user):
        """Deve gerar JWT com estrutura correta"""
        # Act
        token = auth_service._generate_jwt(sample_user)
        
        # Assert - Usar options para desabilitar validação de timestamp
        decoded = jwt.decode(
            token, 
            "test_secret_key", 
            algorithms=["HS256"],
            options={"verify_iat": False}
        )
        
        assert decoded["user_id"] == str(sample_user.id.value)
        assert decoded["email"] == sample_user.email
        assert decoded["role"] == sample_user.role.value
        assert decoded["primary_municipality_id"] == str(sample_user.primary_municipality_id.value)
        assert decoded["municipality_ids"] == [str(mid.value) for mid in sample_user.municipality_ids]
        assert decoded["iss"] == "intelligent-document-search"
        assert decoded["sub"] == str(sample_user.id.value)
        assert "iat" in decoded
        assert "exp" in decoded

    def test_generate_jwt_expiry(self, auth_service, sample_user):
        """Deve gerar JWT com expiração correta"""
        # Act
        token = auth_service._generate_jwt(sample_user)
        
        # Assert - Usar options para desabilitar validação de timestamp
        decoded = jwt.decode(
            token, 
            "test_secret_key", 
            algorithms=["HS256"],
            options={"verify_iat": False}
        )
        
        iat = datetime.fromtimestamp(decoded["iat"])
        exp = datetime.fromtimestamp(decoded["exp"])
        
        expected_expiry = iat + timedelta(days=3)
        assert abs((exp - expected_expiry).total_seconds()) < 1  # Tolerância de 1 segundo

    def test_verify_password_success(self, auth_service):
        """Deve verificar senha correta"""
        # Arrange
        password = "test_password"
        password_hash = auth_service.hash_password(password)
        
        # Act
        result = auth_service._verify_password(password, password_hash)
        
        # Assert
        assert result is True

    def test_verify_password_failure(self, auth_service):
        """Deve falhar com senha incorreta"""
        # Arrange
        password = "test_password"
        wrong_password = "wrong_password"
        password_hash = auth_service.hash_password(password)
        
        # Act
        result = auth_service._verify_password(wrong_password, password_hash)
        
        # Assert
        assert result is False

    def test_verify_password_invalid_hash(self, auth_service):
        """Deve falhar com hash inválido"""
        # Act
        result = auth_service._verify_password("password", "invalid_hash")
        
        # Assert
        assert result is False

    def test_hash_password_generates_different_hashes(self, auth_service):
        """Deve gerar hashes diferentes para a mesma senha"""
        # Arrange
        password = "test_password"
        
        # Act
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Assert
        assert hash1 != hash2
        assert auth_service._verify_password(password, hash1)
        assert auth_service._verify_password(password, hash2)

    def test_hash_password_bcrypt_format(self, auth_service):
        """Deve gerar hash no formato bcrypt"""
        # Act
        password_hash = auth_service.hash_password("test_password")
        
        # Assert
        assert password_hash.startswith("$2b$")
        assert len(password_hash) == 60  # Tamanho padrão do bcrypt

    @pytest.mark.asyncio
    async def test_verify_google_token_not_configured(self, mock_user_repository):
        """Deve falhar se Google OAuth2 não configurado"""
        # Arrange
        auth_service = AuthenticationService(
            user_repository=mock_user_repository,
            jwt_secret="test_secret",
            google_client_id=None  # Não configurado
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Google OAuth2 não configurado"):
            await auth_service._verify_google_token("token")

    @pytest.mark.asyncio
    async def test_verify_google_token_invalid_issuer(self, auth_service):
        """Deve falhar com issuer inválido"""
        # Arrange
        mock_idinfo = {
            "sub": "123456",
            "email": "user@test.com",
            "iss": "malicious.com"  # Issuer inválido
        }
        
        with patch('google.oauth2.id_token.verify_oauth2_token', return_value=mock_idinfo):
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Token Google inválido"):
                await auth_service._verify_google_token("token")

    @pytest.mark.asyncio
    async def test_verify_google_token_success(self, auth_service):
        """Deve verificar token Google com sucesso"""
        # Arrange
        mock_idinfo = {
            "sub": "123456",
            "email": "user@gmail.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch('google.oauth2.id_token.verify_oauth2_token', return_value=mock_idinfo):
            # Act
            result = await auth_service._verify_google_token("valid_token")
            
            # Assert
            assert result == mock_idinfo

    @pytest.mark.asyncio
    async def test_verify_google_token_value_error(self, auth_service):
        """Deve falhar com ValueError do Google"""
        # Arrange
        with patch('google.oauth2.id_token.verify_oauth2_token', side_effect=ValueError("Invalid token")):
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Token Google inválido: Invalid token"):
                await auth_service._verify_google_token("invalid_token")

    @pytest.mark.asyncio
    async def test_authenticate_email_password_repository_exception(self, auth_service, mock_user_repository):
        """Deve tratar exceções do repositório"""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(side_effect=Exception("Database error"))
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Erro interno na autenticação"):
            await auth_service.authenticate_email_password("user@test.com", "password")

    @pytest.mark.asyncio
    async def test_authenticate_google_oauth2_repository_exception(self, auth_service, mock_user_repository):
        """Deve tratar exceções do repositório no Google OAuth2"""
        # Arrange
        mock_user_repository.find_by_google_id = AsyncMock(side_effect=Exception("Database error"))
        
        google_token_info = {
            "sub": "google_123456",
            "email": "user@gmail.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch.object(auth_service, '_verify_google_token', return_value=google_token_info):
            # Act & Assert
            with pytest.raises(AuthenticationError, match="Erro interno na autenticação"):
                await auth_service.authenticate_google_oauth2("google_token")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_repository_exception(self, auth_service, mock_user_repository, sample_user):
        """Deve tratar exceções do repositório na verificação JWT"""
        # Arrange
        token = "valid_token"
        mock_user_repository.find_by_id = AsyncMock(side_effect=Exception("Database error"))
        
        # Mock jwt.decode para retornar payload válido
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(sample_user.id.value),
                "exp": (datetime.utcnow() + timedelta(days=1)).timestamp()
            }
            
            # Act & Assert
            with pytest.raises(InvalidTokenError, match="Erro na verificação do token"):
                await auth_service.verify_jwt_token(token)

    def test_jwt_payload_with_no_municipality(self, auth_service):
        """Deve gerar JWT corretamente para usuário sem prefeitura"""
        # Arrange
        user = User(
            id=UserId(uuid4()),
            email="user@test.com",
            full_name="Test User",
            role=UserRole.SUPERUSER,
            primary_municipality_id=None,
            municipality_ids=[],
            password_hash="hashed_password"
        )
        
        # Act
        token = auth_service._generate_jwt(user)
        
        # Assert - Usar options para desabilitar validação de timestamp
        decoded = jwt.decode(
            token, 
            "test_secret_key", 
            algorithms=["HS256"],
            options={"verify_iat": False}
        )
        assert decoded["primary_municipality_id"] is None
        assert decoded["municipality_ids"] == []

    @pytest.mark.asyncio
    async def test_google_oauth2_updates_user_data(self, auth_service, mock_user_repository, google_user):
        """Deve atualizar dados do usuário Google se necessário"""
        # Arrange
        google_user.google_id = "old_google_id"  # ID antigo
        mock_user_repository.find_by_google_id = AsyncMock(return_value=google_user)
        mock_user_repository.save = AsyncMock()
        
        google_token_info = {
            "sub": "new_google_id",  # ID novo
            "email": "user@gmail.com",
            "email_verified": True,
            "iss": "accounts.google.com"
        }
        
        with patch.object(auth_service, '_verify_google_token', return_value=google_token_info):
            # Act
            user, token = await auth_service.authenticate_google_oauth2("google_token")
            
            # Assert
            assert user.google_id == "new_google_id"
            assert user.email_verified is True
            assert mock_user_repository.save.call_count == 2  # Uma para atualizar dados, outra para last_login
