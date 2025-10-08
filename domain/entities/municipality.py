from dataclasses import dataclass, field
from datetime import date, datetime

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.municipality_id import MunicipalityId


@dataclass
class Municipality:
    """Municipality entity for multi-tenancy"""

    id: MunicipalityId
    name: str
    token_quota: int
    tokens_consumed: int = 0
    active: bool = True
    monthly_token_limit: int = 20000
    contract_date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validates municipality business rules"""
        if not self.name or len(self.name.strip()) == 0:
            raise BusinessRuleViolationError("Municipality name is required")

        if len(self.name) > 255:
            raise BusinessRuleViolationError(
                "Municipality name cannot exceed 255 characters"
            )

        if self.token_quota < 0:
            raise BusinessRuleViolationError("Token quota cannot be negative")

        if self.tokens_consumed < 0:
            raise BusinessRuleViolationError("Tokens consumed cannot be negative")

        if self.tokens_consumed > self.token_quota:
            raise BusinessRuleViolationError("Tokens consumed cannot exceed quota")

        if self.monthly_token_limit <= 0:
            raise BusinessRuleViolationError("Monthly limit must be positive")

        if self.monthly_token_limit > 1000000:
            raise BusinessRuleViolationError("Monthly limit cannot exceed 1M tokens")

        if self.contract_date > date.today():
            raise BusinessRuleViolationError("Contract date cannot be in the future")

    @classmethod
    def create(
        cls, name: str, token_quota: int = 10000, active: bool = True
    ) -> "Municipality":
        """Factory method to create new Municipality"""
        return cls(
            id=MunicipalityId.generate(),
            name=name.strip(),
            token_quota=token_quota,
            tokens_consumed=0,
            active=active,
        )

    def can_renew_period(self) -> bool:
        """Only renews if active (payment up to date)"""
        return self.active

    def calculate_next_due_date(self) -> date:
        """Calculates next due date based on contract date"""
        today = date.today()

        if today.day >= self.contract_date.day:
            if today.month == 12:
                return date(today.year + 1, 1, self.contract_date.day)
            else:
                try:
                    return date(today.year, today.month + 1, self.contract_date.day)
                except ValueError:
                    next_month = today.month + 1 if today.month < 12 else 1
                    next_year = today.year if today.month < 12 else today.year + 1
                    return date(next_year, next_month, 28)
        else:
            return date(today.year, today.month, self.contract_date.day)

    def update_monthly_limit(self, new_limit: int) -> None:
        """Updates monthly limit with validation"""
        if new_limit <= 0:
            raise BusinessRuleViolationError("New limit must be positive")

        if new_limit > 1000000:
            raise BusinessRuleViolationError("Limit cannot exceed 1M tokens")

        self.monthly_token_limit = new_limit
        self.updated_at = datetime.utcnow()

    def consume_tokens(self, amount: int) -> None:
        """Consumes tokens from municipality quota"""
        if amount <= 0:
            raise BusinessRuleViolationError("Token amount must be positive")

        if self.tokens_consumed + amount > self.token_quota:
            raise BusinessRuleViolationError(
                f"Token quota exceeded. Available: {self.remaining_tokens}, "
                f"Requested: {amount}"
            )

        self.tokens_consumed += amount
        self.updated_at = datetime.utcnow()

    def increase_quota(self, new_quota: int) -> None:
        """Increases municipality token quota"""
        if new_quota < self.tokens_consumed:
            raise BusinessRuleViolationError(
                f"New quota ({new_quota}) cannot be less than already consumed tokens ({self.tokens_consumed})"
            )

        self.token_quota = new_quota
        self.updated_at = datetime.utcnow()

    def reset_consumption(self) -> None:
        """Resets token consumption (useful for monthly renewal)"""
        self.tokens_consumed = 0
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivates municipality"""
        self.active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activates municipality"""
        self.active = True
        self.updated_at = datetime.utcnow()

    @property
    def remaining_tokens(self) -> int:
        """Calculates remaining tokens in quota"""
        return max(0, self.token_quota - self.tokens_consumed)

    @property
    def consumption_percentage(self) -> float:
        """Calculates quota consumption percentage"""
        if self.token_quota == 0:
            return 0.0
        return (self.tokens_consumed / self.token_quota) * 100

    @property
    def quota_exhausted(self) -> bool:
        """Checks if quota is exhausted"""
        return self.tokens_consumed >= self.token_quota

    @property
    def quota_critical(self) -> bool:
        """Checks if near limit (>90%)"""
        return self.consumption_percentage > 90.0

    def can_consume(self, amount: int) -> bool:
        """Checks if can consume specified token amount"""
        return self.active and self.tokens_consumed + amount <= self.token_quota
