from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MunicipalityId:
    """Value object for Municipality ID"""

    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("MunicipalityId must be a valid UUID")

    @classmethod
    def generate(cls) -> "MunicipalityId":
        """Generates a new unique ID for Municipality"""
        return cls(uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "MunicipalityId":
        """Creates MunicipalityId from string"""
        try:
            return cls(UUID(id_str))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid string for MunicipalityId: {id_str}") from e

    @classmethod
    def from_uuid(cls, uuid_obj: UUID) -> "MunicipalityId":
        """Creates MunicipalityId from UUID"""
        return cls(uuid_obj)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, MunicipalityId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
