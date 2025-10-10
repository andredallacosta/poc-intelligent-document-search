import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from domain.entities.user import User
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole


class TestUserEntity:
    """Testes unitários para a entidade User"""

    def test_user_creation_with_valid_data(self):
        """Deve criar usuário com dados válidos"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD
        )
        
        assert user.email == "user@test.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER
        assert user.primary_municipality_id == municipality_id
        assert municipality_id in user.municipality_ids
        assert user.password_hash == "hashed_password"
        assert user.auth_provider == AuthProvider.EMAIL_PASSWORD
        assert user.is_active is True
        assert user.email_verified is False

    def test_user_creation_with_invalid_email(self):
        """Deve falhar com email inválido"""
        with pytest.raises(BusinessRuleViolationError, match="Email inválido"):
            User(
                email="invalid-email",
                full_name="Test User",
                password_hash="hashed_password"
            )

    def test_user_creation_with_empty_email(self):
        """Deve falhar com email vazio"""
        with pytest.raises(BusinessRuleViolationError, match="Email inválido"):
            User(
                email="",
                full_name="Test User",
                password_hash="hashed_password"
            )

    def test_user_creation_with_invalid_email_format(self):
        """Deve falhar com formato de email inválido"""
        with pytest.raises(BusinessRuleViolationError, match="Email deve ter formato válido"):
            User(
                email="invalid@",
                full_name="Test User",
                password_hash="hashed_password"
            )

    def test_user_creation_with_long_email(self):
        """Deve falhar com email muito longo"""
        long_email = "a" * 250 + "@test.com"  # > 255 chars
        with pytest.raises(BusinessRuleViolationError, match="Email não pode ter mais de 255 caracteres"):
            User(
                email=long_email,
                full_name="Test User",
                password_hash="hashed_password"
            )

    def test_user_creation_with_short_name(self):
        """Deve falhar com nome muito curto"""
        with pytest.raises(BusinessRuleViolationError, match="Nome deve ter pelo menos 2 caracteres"):
            User(
                email="user@test.com",
                full_name="A",
                password_hash="hashed_password"
            )

    def test_user_creation_with_empty_name(self):
        """Deve falhar com nome vazio"""
        with pytest.raises(BusinessRuleViolationError, match="Nome deve ter pelo menos 2 caracteres"):
            User(
                email="user@test.com",
                full_name="",
                password_hash="hashed_password"
            )

    def test_user_creation_with_long_name(self):
        """Deve falhar com nome muito longo"""
        long_name = "A" * 256  # > 255 chars
        with pytest.raises(BusinessRuleViolationError, match="Nome não pode ter mais de 255 caracteres"):
            User(
                email="user@test.com",
                full_name=long_name,
                password_hash="hashed_password"
            )

    def test_email_password_provider_requires_password_hash(self):
        """Deve falhar se provider email/senha não tem password hash"""
        with pytest.raises(BusinessRuleViolationError, match="Password hash obrigatório para email/senha"):
            User(
                email="user@test.com",
                full_name="Test User",
                auth_provider=AuthProvider.EMAIL_PASSWORD,
                password_hash=None
            )

    def test_google_oauth2_provider_requires_google_id(self):
        """Deve falhar se provider Google OAuth2 não tem google_id"""
        with pytest.raises(BusinessRuleViolationError, match="Google ID obrigatório para OAuth2"):
            User(
                email="user@test.com",
                full_name="Test User",
                auth_provider=AuthProvider.GOOGLE_OAUTH2,
                google_id=None
            )

    def test_primary_municipality_added_to_list(self):
        """Deve adicionar prefeitura principal à lista automaticamente"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="user@test.com",
            full_name="Test User",
            primary_municipality_id=municipality_id,
            password_hash="hashed_password"
        )
        
        assert municipality_id in user.municipality_ids

    def test_user_role_user_cannot_have_multiple_municipalities(self):
        """Usuário comum não pode ter múltiplas prefeituras"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        with pytest.raises(BusinessRuleViolationError, match="Usuários comuns só podem ter uma prefeitura"):
            User(
                email="user@test.com",
                full_name="Test User",
                role=UserRole.USER,
                primary_municipality_id=municipality_1,
                municipality_ids=[municipality_1, municipality_2],
                password_hash="hashed_password"
            )

    def test_invitation_token_requires_expiration(self):
        """Token de convite deve ter data de expiração"""
        with pytest.raises(BusinessRuleViolationError, match="Token de convite deve ter data de expiração"):
            User(
                email="user@test.com",
                full_name="Test User",
                invitation_token="token123",
                invitation_expires_at=None,
                password_hash="hashed_password"
            )

    def test_can_access_municipality(self):
        """Deve verificar acesso à prefeitura corretamente"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        user = User(
            email="user@test.com",
            full_name="Test User",
            municipality_ids=[municipality_1],
            password_hash="hashed_password"
        )
        
        assert user.can_access_municipality(municipality_1) is True
        assert user.can_access_municipality(municipality_2) is False

    def test_can_manage_users_superuser(self):
        """SUPERUSER pode gerenciar usuários"""
        user = User(
            email="admin@test.com",
            full_name="Super Admin",
            role=UserRole.SUPERUSER,
            password_hash="hashed_password"
        )
        
        assert user.can_manage_users() is True

    def test_can_manage_users_admin(self):
        """ADMIN pode gerenciar usuários"""
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            password_hash="hashed_password"
        )
        
        assert user.can_manage_users() is True

    def test_can_manage_users_regular_user(self):
        """Usuário comum não pode gerenciar usuários"""
        user = User(
            email="user@test.com",
            full_name="Regular User",
            role=UserRole.USER,
            password_hash="hashed_password"
        )
        
        assert user.can_manage_users() is False

    def test_can_manage_municipality_superuser(self):
        """SUPERUSER pode gerenciar qualquer prefeitura"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="admin@test.com",
            full_name="Super Admin",
            role=UserRole.SUPERUSER,
            password_hash="hashed_password"
        )
        
        assert user.can_manage_municipality(municipality_id) is True

    def test_can_manage_municipality_admin_own(self):
        """ADMIN pode gerenciar suas próprias prefeituras"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            municipality_ids=[municipality_id],
            password_hash="hashed_password"
        )
        
        assert user.can_manage_municipality(municipality_id) is True

    def test_can_manage_municipality_admin_other(self):
        """ADMIN não pode gerenciar prefeituras de outros"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            municipality_ids=[municipality_1],
            password_hash="hashed_password"
        )
        
        assert user.can_manage_municipality(municipality_2) is False

    def test_can_manage_municipality_regular_user(self):
        """Usuário comum não pode gerenciar prefeituras"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="user@test.com",
            full_name="Regular User",
            role=UserRole.USER,
            municipality_ids=[municipality_id],
            password_hash="hashed_password"
        )
        
        assert user.can_manage_municipality(municipality_id) is False

    def test_add_municipality_success_admin(self):
        """ADMIN pode adicionar prefeitura"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            municipality_ids=[municipality_1],
            password_hash="hashed_password"
        )
        
        user.add_municipality(municipality_2)
        assert municipality_2 in user.municipality_ids

    def test_add_municipality_fail_regular_user(self):
        """Usuário comum não pode adicionar prefeitura"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        user = User(
            email="user@test.com",
            full_name="Regular User",
            role=UserRole.USER,
            municipality_ids=[municipality_1],
            password_hash="hashed_password"
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Usuários comuns não podem ter múltiplas prefeituras"):
            user.add_municipality(municipality_2)

    def test_remove_municipality_success(self):
        """Deve remover prefeitura secundária com sucesso"""
        municipality_1 = MunicipalityId(uuid4())
        municipality_2 = MunicipalityId(uuid4())
        
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_1,
            municipality_ids=[municipality_1, municipality_2],
            password_hash="hashed_password"
        )
        
        user.remove_municipality(municipality_2)
        assert municipality_2 not in user.municipality_ids
        assert municipality_1 in user.municipality_ids

    def test_remove_municipality_fail_primary(self):
        """Não deve permitir remover prefeitura principal"""
        municipality_id = MunicipalityId(uuid4())
        
        user = User(
            email="admin@test.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password"
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Não é possível remover prefeitura principal"):
            user.remove_municipality(municipality_id)

    def test_activate_account_success_email_password(self):
        """Deve ativar conta com email/senha com sucesso"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            is_active=False,
            email_verified=False,
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=1),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            password_hash="temp_hash"  # Necessário para validação inicial
        )
        
        user.activate_account(
            password_hash="new_password_hash",
            auth_provider=AuthProvider.EMAIL_PASSWORD
        )
        
        assert user.is_active is True
        assert user.email_verified is True
        assert user.invitation_token is None
        assert user.invitation_expires_at is None
        assert user.password_hash == "new_password_hash"
        assert user.auth_provider == AuthProvider.EMAIL_PASSWORD
        assert user.google_id is None

    def test_activate_account_success_google_oauth2(self):
        """Deve ativar conta com Google OAuth2 com sucesso"""
        user = User(
            email="user@gmail.com",
            full_name="Google User",
            is_active=False,
            email_verified=False,
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=1),
            auth_provider=AuthProvider.EMAIL_PASSWORD,  # Temporário
            password_hash="temp_hash"  # Temporário
        )
        
        user.activate_account(
            google_id="google_123456",
            auth_provider=AuthProvider.GOOGLE_OAUTH2
        )
        
        assert user.is_active is True
        assert user.email_verified is True
        assert user.invitation_token is None
        assert user.invitation_expires_at is None
        assert user.auth_provider == AuthProvider.GOOGLE_OAUTH2
        assert user.google_id == "google_123456"
        assert user.password_hash is None  # Removido para Google OAuth2

    def test_activate_account_fail_no_invitation(self):
        """Deve falhar se não tem convite pendente"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            password_hash="hashed_password"
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Usuário não tem convite pendente"):
            user.activate_account("new_password_hash")

    def test_activate_account_fail_expired_invitation(self):
        """Deve falhar se convite expirado"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() - timedelta(days=1),  # Expirado
            password_hash="hashed_password"
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Convite expirado"):
            user.activate_account("new_password_hash")

    def test_activate_account_fail_email_password_no_hash(self):
        """Deve falhar se email/senha sem password hash"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=1),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            password_hash="temp_hash"  # Necessário para validação inicial
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Password obrigatório para ativação"):
            user.activate_account(
                password_hash=None,
                auth_provider=AuthProvider.EMAIL_PASSWORD
            )

    def test_activate_account_fail_google_oauth2_no_google_id(self):
        """Deve falhar se Google OAuth2 sem google_id"""
        user = User(
            email="user@gmail.com",
            full_name="Google User",
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=1),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            password_hash="temp_hash"
        )
        
        with pytest.raises(BusinessRuleViolationError, match="Google ID obrigatório para ativação"):
            user.activate_account(
                google_id=None,
                auth_provider=AuthProvider.GOOGLE_OAUTH2
            )

    def test_activate_account_backwards_compatibility(self):
        """Deve manter compatibilidade com ativação antiga (apenas password_hash)"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            is_active=False,
            email_verified=False,
            invitation_token="token123",
            invitation_expires_at=datetime.utcnow() + timedelta(days=1),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            password_hash="temp_hash"
        )
        
        # Ativação no formato antigo (apenas password_hash)
        user.activate_account("new_password_hash")
        
        assert user.is_active is True
        assert user.email_verified is True
        assert user.password_hash == "new_password_hash"
        assert user.auth_provider == AuthProvider.EMAIL_PASSWORD

    def test_deactivate_user(self):
        """Deve desativar usuário"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            is_active=True,
            password_hash="hashed_password"
        )
        
        user.deactivate()
        assert user.is_active is False

    def test_update_last_login(self):
        """Deve atualizar timestamp do último login"""
        user = User(
            email="user@test.com",
            full_name="Test User",
            password_hash="hashed_password"
        )
        
        old_updated_at = user.updated_at
        user.update_last_login()
        
        assert user.last_login is not None
        assert user.updated_at > old_updated_at

    def test_create_with_invitation_factory(self):
        """Deve criar usuário com convite usando factory method (sem auth_provider definido)"""
        municipality_id = MunicipalityId(uuid4())
        invited_by = UserId(uuid4())
        
        user = User.create_with_invitation(
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            invited_by=invited_by
        )
        
        assert user.email == "user@test.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER
        assert user.primary_municipality_id == municipality_id
        assert municipality_id in user.municipality_ids
        assert user.is_active is False
        assert user.email_verified is False
        assert user.invitation_token is not None
        assert user.invitation_expires_at is not None
        assert user.invited_by == invited_by
        # Auth provider temporário - será definido na ativação
        assert user.auth_provider == AuthProvider.EMAIL_PASSWORD
        assert user.password_hash is not None  # Hash temporário

    def test_create_with_invitation_flexible_activation_flow(self):
        """Deve testar fluxo completo de criação e ativação flexível"""
        municipality_id = MunicipalityId(uuid4())
        invited_by = UserId(uuid4())
        
        # 1. Criação do usuário com convite (sem definir auth_provider)
        user = User.create_with_invitation(
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER,
            primary_municipality_id=municipality_id,
            invited_by=invited_by
        )
        
        # Usuário criado mas não ativo
        assert user.is_active is False
        assert user.invitation_token is not None
        
        # 2. Usuário escolhe ativar com Google OAuth2
        user.activate_account(
            google_id="google_123456",
            auth_provider=AuthProvider.GOOGLE_OAUTH2
        )
        
        # Verificações após ativação
        assert user.is_active is True
        assert user.email_verified is True
        assert user.auth_provider == AuthProvider.GOOGLE_OAUTH2
        assert user.google_id == "google_123456"
        assert user.password_hash is None  # Removido para OAuth2
        assert user.invitation_token is None

    def test_compatibility_properties(self):
        """Deve manter compatibilidade com propriedades antigas"""
        municipality_id = MunicipalityId(uuid4())
        user = User(
            email="user@test.com",
            full_name="Test User",
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            is_active=True,
            password_hash="hashed_password"
        )
        
        # Testa propriedades de compatibilidade
        assert user.name == "Test User"
        assert user.municipality_id == municipality_id
        assert user.active is True
        
        # Testa setters de compatibilidade
        user.name = "New Name"
        assert user.full_name == "New Name"
        
        new_municipality = MunicipalityId(uuid4())
        user.municipality_id = new_municipality
        assert user.primary_municipality_id == new_municipality
        assert new_municipality in user.municipality_ids
        
        user.active = False
        assert user.is_active is False

    def test_email_validation_edge_cases(self):
        """Testa casos extremos de validação de email"""
        valid_emails = [
            "user@test.com",
            "user.name@test.com",
            "user+tag@test.com",
            "user123@test-domain.com",
            "user@subdomain.test.com"
        ]
        
        for email in valid_emails:
            user = User(
                email=email,
                full_name="Test User",
                password_hash="hashed_password"
            )
            assert user.email == email

    def test_business_rules_comprehensive(self):
        """Testa validações de regras de negócio de forma abrangente"""
        municipality_id = MunicipalityId(uuid4())
        
        # Usuário válido completo
        user = User(
            email="admin@test.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
            primary_municipality_id=municipality_id,
            municipality_ids=[municipality_id],
            password_hash="hashed_password",
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            is_active=True,
            email_verified=True
        )
        
        # Verifica que todas as validações passaram
        assert user.email == "admin@test.com"
        assert user.role == UserRole.ADMIN
        assert user.can_manage_users() is True
        assert user.can_manage_municipality(municipality_id) is True
        assert user.can_access_municipality(municipality_id) is True