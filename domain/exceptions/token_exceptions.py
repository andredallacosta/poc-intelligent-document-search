from domain.exceptions.business_exceptions import BusinessRuleViolationError


class TokenError(BusinessRuleViolationError):
    """Base exception for token-related errors"""

    pass


class TokenLimitExceededError(TokenError):
    """Exception raised when token limit is exceeded"""

    def __init__(self, message: str = "Token limit exceeded"):
        super().__init__(message)
        self.error_code = "TOKEN_LIMIT_EXCEEDED"


class MunicipalityInactiveError(TokenError):
    """Exception raised when municipality is inactive"""

    def __init__(self, message: str = "Municipality is inactive"):
        super().__init__(message)
        self.error_code = "MUNICIPALITY_INACTIVE"


class TokenLockError(TokenError):
    """Exception raised when unable to acquire lock"""

    def __init__(self, message: str = "Error in concurrency control"):
        super().__init__(message)
        self.error_code = "TOKEN_LOCK_ERROR"


class TokenReservationError(TokenError):
    """Exception raised in token reservation errors"""

    def __init__(self, message: str = "Error in token reservation"):
        super().__init__(message)
        self.error_code = "TOKEN_RESERVATION_ERROR"
