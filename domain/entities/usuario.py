import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.value_objects.usuario_id import UsuarioId


@dataclass
class Usuario:
    """Entidade Usuario para multi-tenancy"""

    id: UsuarioId
    prefeitura_id: Optional[PrefeituraId]
    nome: str
    email: str
    senha_hash: Optional[str] = None  # NULL até implementar autenticação
    ativo: bool = True
    criado_em: datetime = field(default_factory=datetime.utcnow)
    atualizado_em: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Valida regras de negócio do Usuario"""
        if not self.nome or len(self.nome.strip()) == 0:
            raise BusinessRuleViolationError("Nome do usuário é obrigatório")

        if len(self.nome) > 255:
            raise BusinessRuleViolationError(
                "Nome do usuário não pode ter mais de 255 caracteres"
            )

        if not self.email or len(self.email.strip()) == 0:
            raise BusinessRuleViolationError("Email do usuário é obrigatório")

        if not self._is_valid_email(self.email):
            raise BusinessRuleViolationError("Email do usuário deve ter formato válido")

        if len(self.email) > 255:
            raise BusinessRuleViolationError(
                "Email do usuário não pode ter mais de 255 caracteres"
            )

    def _is_valid_email(self, email: str) -> bool:
        """Valida formato do email"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email.strip()) is not None

    @classmethod
    def create(
        cls,
        nome: str,
        email: str,
        prefeitura_id: Optional[PrefeituraId] = None,
        ativo: bool = True,
    ) -> "Usuario":
        """Factory method para criar novo Usuario"""
        return cls(
            id=UsuarioId.generate(),
            prefeitura_id=prefeitura_id,
            nome=nome.strip(),
            email=email.strip().lower(),
            ativo=ativo,
        )

    @classmethod
    def create_anonimo(cls, nome: str = "Usuário Anônimo") -> "Usuario":
        """Cria usuário anônimo (sem prefeitura)"""
        # Email temporário único para usuários anônimos
        email_anonimo = f"anonimo+{UsuarioId.generate()}@temp.local"
        return cls.create(
            nome=nome, email=email_anonimo, prefeitura_id=None, ativo=True
        )

    def vincular_prefeitura(self, prefeitura_id: PrefeituraId) -> None:
        """Vincula usuário a uma prefeitura"""
        if not isinstance(prefeitura_id, PrefeituraId):
            raise BusinessRuleViolationError(
                "ID da prefeitura deve ser um PrefeituraId válido"
            )

        self.prefeitura_id = prefeitura_id
        self.atualizado_em = datetime.utcnow()

    def desvincular_prefeitura(self) -> None:
        """Remove vinculação com prefeitura (torna anônimo)"""
        self.prefeitura_id = None
        self.atualizado_em = datetime.utcnow()

    def atualizar_email(self, novo_email: str) -> None:
        """Atualiza email do usuário"""
        novo_email = novo_email.strip().lower()

        if not self._is_valid_email(novo_email):
            raise BusinessRuleViolationError("Novo email deve ter formato válido")

        if len(novo_email) > 255:
            raise BusinessRuleViolationError(
                "Novo email não pode ter mais de 255 caracteres"
            )

        self.email = novo_email
        self.atualizado_em = datetime.utcnow()

    def atualizar_nome(self, novo_nome: str) -> None:
        """Atualiza nome do usuário"""
        novo_nome = novo_nome.strip()

        if not novo_nome:
            raise BusinessRuleViolationError("Novo nome é obrigatório")

        if len(novo_nome) > 255:
            raise BusinessRuleViolationError(
                "Novo nome não pode ter mais de 255 caracteres"
            )

        self.nome = novo_nome
        self.atualizado_em = datetime.utcnow()

    def definir_senha(self, senha_hash: str) -> None:
        """Define hash da senha do usuário"""
        if not senha_hash or len(senha_hash.strip()) == 0:
            raise BusinessRuleViolationError("Hash da senha é obrigatório")

        self.senha_hash = senha_hash.strip()
        self.atualizado_em = datetime.utcnow()

    def desativar(self) -> None:
        """Desativa o usuário"""
        self.ativo = False
        self.atualizado_em = datetime.utcnow()

    def ativar(self) -> None:
        """Ativa o usuário"""
        self.ativo = True
        self.atualizado_em = datetime.utcnow()

    @property
    def is_anonimo(self) -> bool:
        """Verifica se é usuário anônimo (sem prefeitura)"""
        return self.prefeitura_id is None

    @property
    def tem_prefeitura(self) -> bool:
        """Verifica se usuário está vinculado a uma prefeitura"""
        return self.prefeitura_id is not None

    @property
    def tem_autenticacao(self) -> bool:
        """Verifica se usuário tem senha configurada"""
        return self.senha_hash is not None and len(self.senha_hash) > 0

    @property
    def email_domain(self) -> str:
        """Extrai domínio do email"""
        return self.email.split("@")[1] if "@" in self.email else ""
