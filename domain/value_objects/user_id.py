from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class UserId:
    """Value object for User ID"""

    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("UserId must be a valid UUID")

    @classmethod
    def generate(cls) -> "UserId":
        """Generates a new unique ID for User"""
        return cls(uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "UserId":
        """Creates UserId from string"""
        try:
            return cls(UUID(id_str))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid string for UserId: {id_str}") from e

    @classmethod
    def from_uuid(cls, uuid_obj: UUID) -> "UserId":
        """Creates UserId from UUID"""
        return cls(uuid_obj)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, UserId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
