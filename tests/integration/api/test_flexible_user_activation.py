from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.entities.user import User
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole
from interface.dependencies.container import Container


class TestFlexibleUserActivationIntegration:
    """Testes de integração para ativação flexível de usuários"""

    @pytest.fixture
    def mock_container(self):
        """Mock do container de dependências"""
        container = Mock(spec=Container)
        # Mock repositories
        container.get_user_repository = Mock()
        container.get_municipality_repository = Mock()
        # Mock services
        container.get_authentication_service = Mock()
        container.get_email_service = Mock()
        # Mock use cases
        container.get_authentication_use_case = Mock()
        container.get_user_management_use_case = Mock()
        return container

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
        """Usuário com convite pendente"""
        municipality_id = MunicipalityId(uuid4())
        return User(
            id=UserId(uuid4()),
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
    async def test_check_invitation_token_valid(self, mock_container, invited_user):
        """Deve verificar token de convite válido"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_repo = AsyncMock()
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_container.get_user_repository.return_value = mock_user_repo
        # Mock invited_by user
        invited_by_user = User(
            id=invited_user.invited_by,
            email="inviter@test.com",
            full_name="Inviter User",
            password_hash="hash",
        )
        mock_user_repo.find_by_id = AsyncMock(return_value=invited_by_user)
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            with TestClient(app) as client:
                # Act
                response = client.get("/auth/check-invitation/invitation_token_123")
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["email"] == invited_user.email
        assert data["user"]["full_name"] == invited_user.full_name
        assert data["invited_by"]["full_name"] == invited_by_user.full_name
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_check_invitation_token_invalid(self, mock_container):
        """Deve retornar erro para token inválido"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_repo = AsyncMock()
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=None)
        mock_container.get_user_repository.return_value = mock_user_repo
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            with TestClient(app) as client:
                # Act
                response = client.get("/auth/check-invitation/invalid_token")
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Token de convite inválido ou expirado"

    @pytest.mark.asyncio
    async def test_check_invitation_token_expired(self, mock_container):
        """Deve retornar erro para token expirado"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        municipality_id = MunicipalityId(uuid4())
        expired_user = User(
            email="expired@test.com",
            full_name="Expired User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            is_active=False,
            invitation_token="expired_token",
            invitation_expires_at=datetime.utcnow() - timedelta(days=1),  # Expirado
            password_hash="temp_hash",
        )
        mock_user_repo = AsyncMock()
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=expired_user)
        mock_container.get_user_repository.return_value = mock_user_repo
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            with TestClient(app) as client:
                # Act
                response = client.get("/auth/check-invitation/expired_token")
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Token de convite inválido ou expirado"

    @pytest.mark.asyncio
    async def test_activate_user_email_password_success(
        self, mock_container, invited_user
    ):
        """Deve ativar usuário com email/senha com sucesso"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_management_use_case = AsyncMock()

        # Create a simple object instead of Mock to avoid serialization issues
        class MockUserDTO:
            def __init__(self):
                self.id = str(invited_user.id.value)
                self.email = invited_user.email
                self.full_name = invited_user.full_name
                self.is_active = True
                self.email_verified = True

            @property
            def __dict__(self):
                return {
                    "id": self.id,
                    "email": self.email,
                    "full_name": self.full_name,
                    "is_active": self.is_active,
                    "email_verified": self.email_verified,
                }

        mock_user_management_use_case.activate_user_account = AsyncMock(
            return_value=MockUserDTO()
        )
        mock_container.get_user_management_use_case.return_value = (
            mock_user_management_use_case
        )
        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "email_password",
            "password": "new_password123",
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Conta ativada com sucesso" in data["message"]
        assert "email e senha" in data["next_step"]
        assert data["user"]["email"] == invited_user.email
        assert data["user"]["is_active"] is True
        # Verifica que o use case foi chamado corretamente
        mock_user_management_use_case.activate_user_account.assert_called_once()
        call_args = mock_user_management_use_case.activate_user_account.call_args[0][0]
        assert call_args.invitation_token == "invitation_token_123"
        assert call_args.auth_provider == "email_password"
        assert call_args.password == "new_password123"

    @pytest.mark.asyncio
    async def test_activate_user_google_oauth2_success(
        self, mock_container, invited_user
    ):
        """Deve ativar usuário com Google OAuth2 com sucesso"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_management_use_case = AsyncMock()

        # Create a simple object instead of Mock to avoid serialization issues
        class MockUserDTO:
            def __init__(self):
                self.id = str(invited_user.id.value)
                self.email = invited_user.email
                self.full_name = invited_user.full_name
                self.is_active = True
                self.email_verified = True

            @property
            def __dict__(self):
                return {
                    "id": self.id,
                    "email": self.email,
                    "full_name": self.full_name,
                    "is_active": self.is_active,
                    "email_verified": self.email_verified,
                }

        mock_user_management_use_case.activate_user_account = AsyncMock(
            return_value=MockUserDTO()
        )
        mock_container.get_user_management_use_case.return_value = (
            mock_user_management_use_case
        )
        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "google_oauth2",
            "google_token": "google_token_123",
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Conta ativada com sucesso" in data["message"]
        assert "Google" in data["next_step"]
        assert data["user"]["email"] == invited_user.email
        assert data["user"]["is_active"] is True
        # Verifica que o use case foi chamado corretamente
        mock_user_management_use_case.activate_user_account.assert_called_once()
        call_args = mock_user_management_use_case.activate_user_account.call_args[0][0]
        assert call_args.invitation_token == "invitation_token_123"
        assert call_args.auth_provider == "google_oauth2"
        assert call_args.google_token == "google_token_123"

    @pytest.mark.asyncio
    async def test_activate_user_invalid_auth_provider(self, mock_container):
        """Deve falhar com auth_provider inválido"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "invalid_provider",
            "password": "password123",
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = lambda: AsyncMock()
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_activate_user_missing_password_for_email_provider(
        self, mock_container
    ):
        """Deve falhar se escolher email/senha mas não fornecer senha"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "email_password",
            # password ausente
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency - mock should raise validation error
            mock_use_case = AsyncMock()
            mock_use_case.activate_user_account = AsyncMock(
                side_effect=ValueError(
                    "Password é obrigatório para auth_provider email_password"
                )
            )
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_use_case
            )
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 400  # Business validation error

    @pytest.mark.asyncio
    async def test_activate_user_missing_google_token(self, mock_container):
        """Deve falhar se escolher Google OAuth2 mas não fornecer token"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "google_oauth2",
            # google_token ausente
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency - mock should raise validation error
            mock_use_case = AsyncMock()
            mock_use_case.activate_user_account = AsyncMock(
                side_effect=ValueError(
                    "Google token é obrigatório para auth_provider google_oauth2"
                )
            )
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_use_case
            )
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 400  # Business validation error

    @pytest.mark.asyncio
    async def test_full_user_creation_and_activation_flow(
        self, mock_container, admin_user
    ):
        """Testa fluxo completo: criação → verificação → ativação"""
        # Arrange
        from interface.api.v1.endpoints.auth import router as auth_router
        from interface.api.v1.endpoints.users import router as users_router

        # Mock para criação de usuário
        mock_user_management_use_case = AsyncMock()
        # Create a proper DTO-like object instead of Mock
        from application.dto.auth_dto import UserListDTO

        created_user_dto = UserListDTO(
            id=str(uuid4()),
            email="newuser@test.com",
            full_name="New User",
            role="user",
            primary_municipality_id=str(admin_user.primary_municipality_id.value),
            municipality_ids=[str(admin_user.primary_municipality_id.value)],
            is_active=False,
            email_verified=False,
            last_login=None,
            created_at=datetime.utcnow().isoformat(),
            has_pending_invitation=True,
            invited_by_name=admin_user.full_name,
        )
        mock_user_management_use_case.create_user_with_invitation = AsyncMock(
            return_value=created_user_dto
        )
        # Mock para verificação de token
        mock_user_repo = AsyncMock()
        invited_user = User(
            email="newuser@test.com",
            full_name="New User",
            role=UserRole.USER,
            is_active=False,
            invitation_token="new_invitation_token",
            invitation_expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by=admin_user.id,
            password_hash="temp_hash",
        )
        mock_user_repo.find_by_invitation_token = AsyncMock(return_value=invited_user)
        mock_user_repo.find_by_id = AsyncMock(return_value=admin_user)

        # Mock para ativação
        class MockActivatedUserDTO:
            def __init__(self):
                self.id = str(invited_user.id.value)
                self.email = "newuser@test.com"
                self.full_name = "New User"
                self.is_active = True
                self.email_verified = True

            @property
            def __dict__(self):
                return {
                    "id": self.id,
                    "email": self.email,
                    "full_name": self.full_name,
                    "is_active": self.is_active,
                    "email_verified": self.email_verified,
                }

        activated_user_dto = MockActivatedUserDTO()
        mock_user_management_use_case.activate_user_account = AsyncMock(
            return_value=activated_user_dto
        )
        mock_container.get_user_management_use_case.return_value = (
            mock_user_management_use_case
        )
        mock_container.get_user_repository.return_value = mock_user_repo
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            # 1. Criar usuário
            users_app = FastAPI()
            users_app.include_router(users_router)
            # Override dependencies for user creation
            from interface.dependencies.container import get_user_management_use_case
            from interface.middleware.auth_middleware import get_authenticated_user

            users_app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            users_app.dependency_overrides[get_authenticated_user] = lambda: admin_user
            with TestClient(users_app) as client:
                create_response = client.post(
                    "/users/create",
                    json={
                        "email": "newuser@test.com",
                        "full_name": "New User",
                        "role": "user",
                        "primary_municipality_id": str(
                            admin_user.primary_municipality_id.value
                        ),
                    },
                )
            assert create_response.status_code == 200
            # 2. Verificar token de convite
            auth_app = FastAPI()
            auth_app.include_router(auth_router)
            with TestClient(auth_app) as client:
                check_response = client.get(
                    "/auth/check-invitation/new_invitation_token"
                )
            assert check_response.status_code == 200
            check_data = check_response.json()
            assert check_data["valid"] is True
            # 3. Ativar conta com Google OAuth2
            auth_app = FastAPI()
            auth_app.include_router(auth_router)
            # Override the dependency for activation
            auth_app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            with TestClient(auth_app) as client:
                activate_response = client.post(
                    "/auth/activate",
                    json={
                        "invitation_token": "new_invitation_token",
                        "auth_provider": "google_oauth2",
                        "google_token": "google_token_123",
                    },
                )
            assert activate_response.status_code == 200
            activate_data = activate_response.json()
            assert "Conta ativada com sucesso" in activate_data["message"]
            assert activate_data["user"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_error_handling_in_activation_flow(self, mock_container):
        """Testa tratamento de erros no fluxo de ativação"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_management_use_case = AsyncMock()
        mock_user_management_use_case.activate_user_account = AsyncMock(
            side_effect=ValueError("Token Google inválido: Invalid token")
        )
        mock_container.get_user_management_use_case.return_value = (
            mock_user_management_use_case
        )
        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "google_oauth2",
            "google_token": "invalid_google_token",
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            with TestClient(app) as client:
                # Act
                response = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "Token Google inválido" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_concurrent_activation_attempts(self, mock_container, invited_user):
        """Testa tentativas concorrentes de ativação"""
        # Arrange
        from interface.api.v1.endpoints.auth import router

        mock_user_management_use_case = AsyncMock()

        # Primeira chamada sucede, segunda falha
        class MockUserDTO:
            def __init__(self):
                self.id = str(invited_user.id.value)
                self.email = invited_user.email
                self.full_name = invited_user.full_name
                self.is_active = True
                self.email_verified = True

            @property
            def __dict__(self):
                return {
                    "id": self.id,
                    "email": self.email,
                    "full_name": self.full_name,
                    "is_active": self.is_active,
                    "email_verified": self.email_verified,
                }

        activated_user_dto = MockUserDTO()
        mock_user_management_use_case.activate_user_account = AsyncMock(
            side_effect=[
                activated_user_dto,  # Primeira chamada sucede
                ValueError("Usuário já está ativo"),  # Segunda chamada falha
            ]
        )
        mock_container.get_user_management_use_case.return_value = (
            mock_user_management_use_case
        )
        activation_data = {
            "invitation_token": "invitation_token_123",
            "auth_provider": "email_password",
            "password": "password123",
        }
        with patch(
            "interface.dependencies.container.get_container",
            return_value=mock_container,
        ):
            app = FastAPI()
            app.include_router(router)
            # Override the dependency
            from interface.dependencies.container import get_user_management_use_case

            app.dependency_overrides[get_user_management_use_case] = (
                lambda: mock_user_management_use_case
            )
            with TestClient(app) as client:
                # Act - Primeira ativação
                response1 = client.post("/auth/activate", json=activation_data)
                # Act - Segunda ativação (deve falhar)
                response2 = client.post("/auth/activate", json=activation_data)
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400
        assert "já está ativo" in response2.json()["detail"]["message"]
