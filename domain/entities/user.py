import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId


@dataclass
class User:
    """User entity for multi-tenancy"""

    id: UserId
    municipality_id: Optional[MunicipalityId]
    name: str
    email: str
    password_hash: Optional[str] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validates user business rules"""
        if not self.name or len(self.name.strip()) == 0:
            raise BusinessRuleViolationError("User name is required")

        if len(self.name) > 255:
            raise BusinessRuleViolationError("User name cannot exceed 255 characters")

        if not self.email or len(self.email.strip()) == 0:
            raise BusinessRuleViolationError("User email is required")

        if not self._is_valid_email(self.email):
            raise BusinessRuleViolationError("User email must have valid format")

        if len(self.email) > 255:
            raise BusinessRuleViolationError("User email cannot exceed 255 characters")

    def _is_valid_email(self, email: str) -> bool:
        """Validates email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email.strip()) is not None

    @classmethod
    def create(
        cls,
        name: str,
        email: str,
        municipality_id: Optional[MunicipalityId] = None,
        active: bool = True,
    ) -> "User":
        """Factory method to create new User"""
        return cls(
            id=UserId.generate(),
            municipality_id=municipality_id,
            name=name.strip(),
            email=email.strip().lower(),
            active=active,
        )

    @classmethod
    def create_anonymous(cls, name: str = "Anonymous User") -> "User":
        """Creates anonymous user (without municipality)"""
        anonymous_email = f"anonymous+{UserId.generate()}@temp.local"
        return cls.create(
            name=name, email=anonymous_email, municipality_id=None, active=True
        )

    def link_municipality(self, municipality_id: MunicipalityId) -> None:
        """Links user to a municipality"""
        if not isinstance(municipality_id, MunicipalityId):
            raise BusinessRuleViolationError(
                "Municipality ID must be a valid MunicipalityId"
            )

        self.municipality_id = municipality_id
        self.updated_at = datetime.utcnow()

    def unlink_municipality(self) -> None:
        """Removes municipality link (makes anonymous)"""
        self.municipality_id = None
        self.updated_at = datetime.utcnow()

    def update_email(self, new_email: str) -> None:
        """Updates user email"""
        new_email = new_email.strip().lower()

        if not self._is_valid_email(new_email):
            raise BusinessRuleViolationError("New email must have valid format")

        if len(new_email) > 255:
            raise BusinessRuleViolationError("New email cannot exceed 255 characters")

        self.email = new_email
        self.updated_at = datetime.utcnow()

    def update_name(self, new_name: str) -> None:
        """Updates user name"""
        new_name = new_name.strip()

        if not new_name:
            raise BusinessRuleViolationError("New name is required")

        if len(new_name) > 255:
            raise BusinessRuleViolationError("New name cannot exceed 255 characters")

        self.name = new_name
        self.updated_at = datetime.utcnow()

    def set_password(self, password_hash: str) -> None:
        """Sets user password hash"""
        if not password_hash or len(password_hash.strip()) == 0:
            raise BusinessRuleViolationError("Password hash is required")

        self.password_hash = password_hash.strip()
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivates user"""
        self.active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activates user"""
        self.active = True
        self.updated_at = datetime.utcnow()

    @property
    def is_anonymous(self) -> bool:
        """Checks if user is anonymous (without municipality)"""
        return self.municipality_id is None

    @property
    def has_municipality(self) -> bool:
        """Checks if user is linked to a municipality"""
        return self.municipality_id is not None

    @property
    def has_authentication(self) -> bool:
        """Checks if user has password configured"""
        return self.password_hash is not None and len(self.password_hash) > 0

    @property
    def email_domain(self) -> str:
        """Extracts email domain"""
        return self.email.split("@")[1] if "@" in self.email else ""
