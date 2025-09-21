from dataclasses import dataclass
from typing import Optional

from domain.exceptions.business_exceptions import BusinessRuleViolationError


@dataclass(frozen=True)
class S3Key:
    
    bucket: str
    key: str
    region: Optional[str] = None
    
    def __post_init__(self):
        self._validate()
    
    def _validate(self):
        if not self.bucket or len(self.bucket.strip()) == 0:
            raise BusinessRuleViolationError("Bucket S3 é obrigatório")
        
        if not self.key or len(self.key.strip()) == 0:
            raise BusinessRuleViolationError("Key S3 é obrigatória")
        
        if len(self.bucket) > 63:
            raise BusinessRuleViolationError("Bucket S3 não pode ter mais de 63 caracteres")
        
        if len(self.key) > 1024:
            raise BusinessRuleViolationError("Key S3 não pode ter mais de 1024 caracteres")
    
    @classmethod
    def create_temp_key(cls, document_id: str, filename: str, bucket: str = "documents", region: str = "us-east-1") -> "S3Key":
        """Cria chave S3 para arquivo temporário"""
        safe_filename = filename.replace(" ", "_").replace("/", "_")
        key = f"temp/{document_id}/{safe_filename}"
        return cls(bucket=bucket, key=key, region=region)
    
    @property
    def full_path(self) -> str:
        """Retorna caminho completo S3"""
        return f"s3://{self.bucket}/{self.key}"
    
    @property
    def url(self) -> str:
        """Retorna URL S3"""
        region_part = f".{self.region}" if self.region and self.region != "us-east-1" else ""
        return f"https://{self.bucket}.s3{region_part}.amazonaws.com/{self.key}"
