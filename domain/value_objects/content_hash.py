import hashlib
import re
from dataclasses import dataclass

from domain.exceptions.business_exceptions import BusinessRuleViolationError


@dataclass(frozen=True)
class ContentHash:
    """Value object para hash de conteúdo de documento"""
    
    algorithm: str
    value: str
    
    def __post_init__(self):
        self._validate()
    
    def _validate(self):
        if not self.algorithm or self.algorithm not in ["sha256", "md5"]:
            raise BusinessRuleViolationError("Algoritmo deve ser 'sha256' ou 'md5'")
        
        if not self.value or len(self.value.strip()) == 0:
            raise BusinessRuleViolationError("Hash value é obrigatório")
        
        # Validar formato do hash
        if self.algorithm == "sha256" and len(self.value) != 64:
            raise BusinessRuleViolationError("Hash SHA256 deve ter 64 caracteres")
        
        if self.algorithm == "md5" and len(self.value) != 32:
            raise BusinessRuleViolationError("Hash MD5 deve ter 32 caracteres")
        
        # Validar se é hexadecimal
        if not re.match(r'^[a-fA-F0-9]+$', self.value):
            raise BusinessRuleViolationError("Hash deve conter apenas caracteres hexadecimais")
    
    @classmethod
    def from_text(cls, text: str, algorithm: str = "sha256") -> "ContentHash":
        """Cria hash a partir de texto normalizado"""
        normalized_text = cls._normalize_text(text)
        
        if algorithm == "sha256":
            hash_value = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        elif algorithm == "md5":
            hash_value = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        else:
            raise BusinessRuleViolationError(f"Algoritmo não suportado: {algorithm}")
        
        return cls(algorithm=algorithm, value=hash_value)
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para cálculo de hash consistente"""
        # Remove formatação, espaços extras, quebras de linha
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Remove caracteres especiais de formatação
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def __str__(self) -> str:
        return f"{self.algorithm}:{self.value}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ContentHash):
            return False
        return self.algorithm == other.algorithm and self.value == other.value
