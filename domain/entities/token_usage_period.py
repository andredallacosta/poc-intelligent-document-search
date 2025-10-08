from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.municipality_id import MunicipalityId

if TYPE_CHECKING:
    from domain.entities.municipality import Municipality


@dataclass
class TokenUsagePeriod:
    """Entity representing a monthly token usage period"""

    municipality_id: MunicipalityId
    period_start: date
    period_end: date
    base_limit: int
    extra_credits: int = 0
    tokens_consumed: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validates period business rules"""
        if self.period_start >= self.period_end:
            raise BusinessRuleViolationError("Start date must be before end date")

        if self.base_limit <= 0:
            raise BusinessRuleViolationError("Base limit must be positive")

        if self.extra_credits < 0:
            raise BusinessRuleViolationError("Extra credits cannot be negative")

        if self.tokens_consumed < 0:
            raise BusinessRuleViolationError("Tokens consumed cannot be negative")

        if self.tokens_consumed > self.total_limit:
            raise BusinessRuleViolationError(
                "Tokens consumed cannot exceed total limit"
            )

        # Validation for period duration (max 45 days to avoid malformed periods)
        if (self.period_end - self.period_start).days > 45:
            raise BusinessRuleViolationError("Period cannot exceed 45 days")

    @property
    def total_limit(self) -> int:
        """Total limit = base + extra credits"""
        return self.base_limit + self.extra_credits

    @property
    def remaining_tokens(self) -> int:
        """Tokens still available in the period"""
        return max(0, self.total_limit - self.tokens_consumed)

    @property
    def usage_percentage(self) -> float:
        """Percentage of tokens already consumed"""
        if self.total_limit == 0:
            return 0.0
        return round((self.tokens_consumed / self.total_limit) * 100, 2)

    @property
    def is_expired(self) -> bool:
        """Checks if the period has expired"""
        return date.today() > self.period_end

    @property
    def days_remaining(self) -> int:
        """Days remaining until expiration"""
        if self.is_expired:
            return 0
        return (self.period_end - date.today()).days

    def consume_tokens(self, amount: int) -> None:
        """Consumes tokens from the period with validation"""
        if amount <= 0:
            raise BusinessRuleViolationError("Amount must be positive")

        if self.tokens_consumed + amount > self.total_limit:
            raise BusinessRuleViolationError(
                f"Consuming {amount} tokens would exceed limit. "
                f"Available: {self.remaining_tokens}, Requested: {amount}"
            )

        self.tokens_consumed += amount
        self.updated_at = datetime.utcnow()

    def add_credits(self, tokens: int, reason: str = None) -> None:
        """Adds extra credits to the period"""
        if tokens <= 0:
            raise BusinessRuleViolationError("Credits must be positive")

        if tokens > 500000:  # Sanity limit for purchases
            raise BusinessRuleViolationError("Maximum 500k tokens per purchase")

        self.extra_credits += tokens
        self.updated_at = datetime.utcnow()

    @classmethod
    def create_new_period(
        cls, municipality: "Municipality", start: date, end: date
    ) -> "TokenUsagePeriod":
        """Factory method to create new period"""
        return cls(
            municipality_id=municipality.id,
            period_start=start,
            period_end=end,
            base_limit=municipality.monthly_token_limit,
            extra_credits=0,  # Always reset extra credits in new period
            tokens_consumed=0,
        )
