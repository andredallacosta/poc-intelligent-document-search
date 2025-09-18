from dataclasses import dataclass, field
from datetime import datetime

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.prefeitura_id import PrefeituraId


@dataclass
class Prefeitura:
    """Entidade Prefeitura para multi-tenancy"""

    id: PrefeituraId
    nome: str
    quota_tokens: int
    tokens_consumidos: int = 0
    ativo: bool = True
    criado_em: datetime = field(default_factory=datetime.utcnow)
    atualizado_em: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Valida regras de negócio da Prefeitura"""
        if not self.nome or len(self.nome.strip()) == 0:
            raise BusinessRuleViolationError("Nome da prefeitura é obrigatório")

        if len(self.nome) > 255:
            raise BusinessRuleViolationError(
                "Nome da prefeitura não pode ter mais de 255 caracteres"
            )

        if self.quota_tokens < 0:
            raise BusinessRuleViolationError("Quota de tokens não pode ser negativa")

        if self.tokens_consumidos < 0:
            raise BusinessRuleViolationError("Tokens consumidos não pode ser negativo")

        if self.tokens_consumidos > self.quota_tokens:
            raise BusinessRuleViolationError(
                "Tokens consumidos não pode exceder a quota"
            )

    @classmethod
    def create(
        cls, nome: str, quota_tokens: int = 10000, ativo: bool = True
    ) -> "Prefeitura":
        """Factory method para criar nova Prefeitura"""
        return cls(
            id=PrefeituraId.generate(),
            nome=nome.strip(),
            quota_tokens=quota_tokens,
            tokens_consumidos=0,
            ativo=ativo,
        )

    def consumir_tokens(self, quantidade: int) -> None:
        """Consome tokens da quota da prefeitura"""
        if quantidade <= 0:
            raise BusinessRuleViolationError("Quantidade de tokens deve ser positiva")

        if self.tokens_consumidos + quantidade > self.quota_tokens:
            raise BusinessRuleViolationError(
                f"Quota de tokens excedida. Disponível: {self.tokens_restantes}, "
                f"Solicitado: {quantidade}"
            )

        self.tokens_consumidos += quantidade
        self.atualizado_em = datetime.utcnow()

    def aumentar_quota(self, nova_quota: int) -> None:
        """Aumenta a quota de tokens da prefeitura"""
        if nova_quota < self.tokens_consumidos:
            raise BusinessRuleViolationError(
                f"Nova quota ({nova_quota}) não pode ser menor que tokens já consumidos ({self.tokens_consumidos})"
            )

        self.quota_tokens = nova_quota
        self.atualizado_em = datetime.utcnow()

    def resetar_consumo(self) -> None:
        """Reseta o consumo de tokens (útil para renovação mensal)"""
        self.tokens_consumidos = 0
        self.atualizado_em = datetime.utcnow()

    def desativar(self) -> None:
        """Desativa a prefeitura"""
        self.ativo = False
        self.atualizado_em = datetime.utcnow()

    def ativar(self) -> None:
        """Ativa a prefeitura"""
        self.ativo = True
        self.atualizado_em = datetime.utcnow()

    @property
    def tokens_restantes(self) -> int:
        """Calcula tokens restantes na quota"""
        return max(0, self.quota_tokens - self.tokens_consumidos)

    @property
    def percentual_consumo(self) -> float:
        """Calcula percentual de consumo da quota"""
        if self.quota_tokens == 0:
            return 0.0
        return (self.tokens_consumidos / self.quota_tokens) * 100

    @property
    def quota_esgotada(self) -> bool:
        """Verifica se a quota está esgotada"""
        return self.tokens_consumidos >= self.quota_tokens

    @property
    def quota_critica(self) -> bool:
        """Verifica se está próximo do limite (>90%)"""
        return self.percentual_consumo > 90.0

    def pode_consumir(self, quantidade: int) -> bool:
        """Verifica se pode consumir determinada quantidade de tokens"""
        return self.ativo and self.tokens_consumidos + quantidade <= self.quota_tokens
