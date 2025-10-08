import pytest
from datetime import datetime
from domain.entities.user import User
from domain.value_objects.user_id import UserId
from domain.value_objects.municipality_id import MunicipalityId
from domain.exceptions.business_exceptions import BusinessRuleViolationError

class TestUser:
    
    def test_create_valid_user(self):
        user_id = UserId.generate()
        municipality_id = MunicipalityId.generate()
        user = User(
            id=user_id,
            municipality_id=municipality_id,
            name="John Doe",
            email="john@example.com"
        )
        
        assert user.id == user_id
        assert user.municipality_id == municipality_id
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password_hash is None
        assert user.active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_create_user_factory_method(self):
        municipality_id = MunicipalityId.generate()
        user = User.create(
            name="Jane Doe",
            email="jane@example.com",
            municipality_id=municipality_id
        )
        
        assert user.name == "Jane Doe"
        assert user.email == "jane@example.com"
        assert user.municipality_id == municipality_id
        assert user.active is True
        assert isinstance(user.id, UserId)
    
    def test_create_user_factory_method_defaults(self):
        user = User.create("Anonymous User", "anon@example.com")
        
        assert user.name == "Anonymous User"
        assert user.email == "anon@example.com"
        assert user.municipality_id is None
        assert user.active is True
    
    def test_create_anonymous_user(self):
        user = User.create_anonymous("Anonymous User")
        
        assert user.name == "Anonymous User"
        assert user.email.startswith("anonymous+")
        assert user.email.endswith("@temp.local")
        assert user.municipality_id is None
        assert user.active is True
    
    def test_empty_name_raises_error(self):
        user_id = UserId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="User name is required"):
            User(id=user_id, municipality_id=None, name="", email="test@example.com")
    
    def test_whitespace_only_name_raises_error(self):
        user_id = UserId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="User name is required"):
            User(id=user_id, municipality_id=None, name="   ", email="test@example.com")
    
    def test_name_too_long_raises_error(self):
        user_id = UserId.generate()
        long_name = "A" * 256
        
        with pytest.raises(BusinessRuleViolationError, match="User name cannot exceed 255 characters"):
            User(id=user_id, municipality_id=None, name=long_name, email="test@example.com")
    
    def test_empty_email_raises_error(self):
        user_id = UserId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="User email is required"):
            User(id=user_id, municipality_id=None, name="Test User", email="")
    
    def test_whitespace_only_email_raises_error(self):
        user_id = UserId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="User email is required"):
            User(id=user_id, municipality_id=None, name="Test User", email="   ")
    
    def test_invalid_email_format_raises_error(self):
        user_id = UserId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="User email must have valid format"):
            User(id=user_id, municipality_id=None, name="Test User", email="invalid-email")
    
    def test_email_too_long_raises_error(self):
        user_id = UserId.generate()
        long_email = "a" * 250 + "@example.com"
        
        with pytest.raises(BusinessRuleViolationError, match="User email cannot exceed 255 characters"):
            User(id=user_id, municipality_id=None, name="Test User", email=long_email)
    
    def test_valid_email_formats(self):
        user_id = UserId.generate()
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@example.org",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            user = User(id=user_id, municipality_id=None, name="Test User", email=email)
            assert user.email == email.lower().strip()
    
    def test_link_municipality_valid(self):
        user = User.create("Test User", "test@example.com")
        municipality_id = MunicipalityId.generate()
        
        user.link_municipality(municipality_id)
        
        assert user.municipality_id == municipality_id
    
    def test_link_municipality_invalid_type_raises_error(self):
        user = User.create("Test User", "test@example.com")
        
        with pytest.raises(BusinessRuleViolationError, match="Municipality ID must be a valid MunicipalityId"):
            user.link_municipality("invalid-id")
    
    def test_unlink_municipality(self):
        municipality_id = MunicipalityId.generate()
        user = User.create("Test User", "test@example.com", municipality_id=municipality_id)
        
        user.unlink_municipality()
        
        assert user.municipality_id is None
    
    def test_update_email_valid(self):
        user = User.create("Test User", "old@example.com")
        
        user.update_email("new@example.com")
        
        assert user.email == "new@example.com"
    
    def test_update_email_invalid_format_raises_error(self):
        user = User.create("Test User", "old@example.com")
        
        with pytest.raises(BusinessRuleViolationError, match="New email must have valid format"):
            user.update_email("invalid-email")
    
    def test_update_email_too_long_raises_error(self):
        user = User.create("Test User", "old@example.com")
        long_email = "a" * 250 + "@example.com"
        
        with pytest.raises(BusinessRuleViolationError, match="New email cannot exceed 255 characters"):
            user.update_email(long_email)
    
    def test_update_name_valid(self):
        user = User.create("Old Name", "test@example.com")
        
        user.update_name("New Name")
        
        assert user.name == "New Name"
    
    def test_update_name_empty_raises_error(self):
        user = User.create("Old Name", "test@example.com")
        
        with pytest.raises(BusinessRuleViolationError, match="New name is required"):
            user.update_name("")
    
    def test_update_name_too_long_raises_error(self):
        user = User.create("Old Name", "test@example.com")
        long_name = "A" * 256
        
        with pytest.raises(BusinessRuleViolationError, match="New name cannot exceed 255 characters"):
            user.update_name(long_name)
    
    def test_set_password_valid(self):
        user = User.create("Test User", "test@example.com")
        
        user.set_password("hashed_password_123")
        
        assert user.password_hash == "hashed_password_123"
    
    def test_set_password_empty_raises_error(self):
        user = User.create("Test User", "test@example.com")
        
        with pytest.raises(BusinessRuleViolationError, match="Password hash is required"):
            user.set_password("")
    
    def test_set_password_whitespace_only_raises_error(self):
        user = User.create("Test User", "test@example.com")
        
        with pytest.raises(BusinessRuleViolationError, match="Password hash is required"):
            user.set_password("   ")
    
    def test_deactivate(self):
        user = User.create("Test User", "test@example.com")
        
        user.deactivate()
        
        assert user.active is False
    
    def test_activate(self):
        user = User.create("Test User", "test@example.com")
        user.deactivate()
        
        user.activate()
        
        assert user.active is True
    
    def test_is_anonymous_property(self):
        user_with_municipality = User.create("Test User", "test@example.com", municipality_id=MunicipalityId.generate())
        anonymous_user = User.create("Anonymous User", "anon@example.com")
        
        assert user_with_municipality.is_anonymous is False
        assert anonymous_user.is_anonymous is True
    
    def test_has_municipality_property(self):
        user_with_municipality = User.create("Test User", "test@example.com", municipality_id=MunicipalityId.generate())
        anonymous_user = User.create("Anonymous User", "anon@example.com")
        
        assert user_with_municipality.has_municipality is True
        assert anonymous_user.has_municipality is False
    
    def test_has_authentication_property(self):
        user_with_password = User.create("Test User", "test@example.com")
        user_with_password.set_password("hashed_password")
        
        user_without_password = User.create("Anonymous User", "anon@example.com")
        
        assert user_with_password.has_authentication is True
        assert user_without_password.has_authentication is False
    
    def test_email_domain_property(self):
        user = User.create("Test User", "user@example.com")
        
        assert user.email_domain == "example.com"
    
    def test_email_domain_without_at_symbol(self):
        user = User.create("Test User", "invalid-email")
        
        assert user.email_domain == ""
