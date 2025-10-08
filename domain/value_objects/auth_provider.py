from enum import Enum


class AuthProvider(Enum):
    """Provedores de autenticação suportados"""
    EMAIL_PASSWORD = "email_password"
    GOOGLE_OAUTH2 = "google_oauth2"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "AuthProvider":
        """Cria AuthProvider a partir de string"""
        for provider in cls:
            if provider.value == value.lower():
                return provider
        raise ValueError(f"Invalid auth provider: {value}")

    def requires_password(self) -> bool:
        """Verifica se o provider requer senha"""
        return self == AuthProvider.EMAIL_PASSWORD

    def requires_google_id(self) -> bool:
        """Verifica se o provider requer Google ID"""
        return self == AuthProvider.GOOGLE_OAUTH2
