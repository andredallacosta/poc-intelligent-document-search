"""
Exceções de regras de negócio do domínio
"""


class BusinessRuleViolationError(Exception):
    """Exceção para violações de regras de negócio"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Detalhes: {self.details}"
        return self.message


class QuotaExceededException(BusinessRuleViolationError):
    """Exceção específica para quota de tokens excedida"""

    def __init__(
        self, quota_atual: int, tokens_solicitados: int, tokens_disponveis: int
    ):
        message = (
            f"Quota de tokens excedida. "
            f"Disponível: {tokens_disponveis}, "
            f"Solicitado: {tokens_solicitados}, "
            f"Quota total: {quota_atual}"
        )
        details = {
            "quota_atual": quota_atual,
            "tokens_solicitados": tokens_solicitados,
            "tokens_disponveis": tokens_disponveis,
        }
        super().__init__(message, details)


class InvalidUserDataException(BusinessRuleViolationError):
    """Exceção para dados inválidos de usuário"""

    def __init__(self, field: str, value: str, reason: str):
        message = f"Dados inválidos para campo '{field}': {reason}"
        details = {"field": field, "value": value, "reason": reason}
        super().__init__(message, details)


class PrefeituraInactiveException(BusinessRuleViolationError):
    """Exceção para operações em prefeitura inativa"""

    def __init__(self, prefeitura_id: str):
        message = f"Prefeitura {prefeitura_id} está inativa"
        details = {"prefeitura_id": prefeitura_id}
        super().__init__(message, details)


class UserInactiveException(BusinessRuleViolationError):
    """Exceção para operações com usuário inativo"""

    def __init__(self, usuario_id: str):
        message = f"Usuário {usuario_id} está inativo"
        details = {"usuario_id": usuario_id}
        super().__init__(message, details)
