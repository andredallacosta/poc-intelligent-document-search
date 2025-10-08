class AuthenticationError(Exception):
    """Exceção base para erros de autenticação"""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Exceção para credenciais inválidas"""

    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message)
        self.error_code = "INVALID_CREDENTIALS"


class InvalidTokenError(AuthenticationError):
    """Exceção para tokens inválidos ou expirados"""

    def __init__(self, message: str = "Token inválido"):
        super().__init__(message)
        self.error_code = "INVALID_TOKEN"


class UserNotFoundError(AuthenticationError):
    """Exceção quando usuário não é encontrado"""

    def __init__(self, message: str = "Usuário não encontrado"):
        super().__init__(message)
        self.error_code = "USER_NOT_FOUND"


class UserInactiveError(AuthenticationError):
    """Exceção quando usuário está inativo"""

    def __init__(self, message: str = "Usuário inativo"):
        super().__init__(message)
        self.error_code = "USER_INACTIVE"


class InsufficientPermissionsError(AuthenticationError):
    """Exceção para falta de permissões"""

    def __init__(self, message: str = "Permissões insuficientes"):
        super().__init__(message)
        self.error_code = "INSUFFICIENT_PERMISSIONS"


class InvitationExpiredError(AuthenticationError):
    """Exceção para convites expirados"""

    def __init__(self, message: str = "Convite expirado"):
        super().__init__(message)
        self.error_code = "INVITATION_EXPIRED"
