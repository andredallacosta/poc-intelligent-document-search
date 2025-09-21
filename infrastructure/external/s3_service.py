import logging
from datetime import datetime, timedelta
from typing import Optional

import aioboto3
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.s3_key import S3Key

logger = logging.getLogger(__name__)


class S3Service:
    """Serviço para operações S3"""
    
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        
        # Configurar credenciais
        self._session_config = {}
        if access_key and secret_key:
            self._session_config = {
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
            }
        
        # Cliente síncrono para operações simples
        self._sync_client = None
    
    def _get_sync_client(self):
        """Retorna cliente S3 síncrono"""
        if not self._sync_client:
            self._sync_client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                **self._session_config
            )
        return self._sync_client
    
    async def _get_async_client(self):
        """Retorna cliente S3 assíncrono"""
        session = aioboto3.Session(**self._session_config)
        return session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url
        )
    
    def generate_presigned_upload_url(
        self,
        s3_key: S3Key,
        content_type: str,
        expires_in: int = 3600
    ) -> tuple[str, datetime]:
        """
        Gera URL presigned para upload direto ao S3
        
        Returns:
            tuple: (upload_url, expires_at)
        """
        try:
            client = self._get_sync_client()
            
            # Configurar condições do upload
            conditions = [
                {"bucket": s3_key.bucket},
                {"key": s3_key.key},
                {"Content-Type": content_type},
                ["content-length-range", 1, 5368709120]  # 1 byte a 5GB
            ]
            
            # Gerar presigned POST (mais seguro que PUT)
            response = client.generate_presigned_post(
                Bucket=s3_key.bucket,
                Key=s3_key.key,
                Fields={"Content-Type": content_type},
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"Presigned URL gerada para {s3_key.key}, expira em {expires_at}")
            
            # Para compatibilidade, retornar URL simples
            # Em produção, o frontend usaria response['url'] + response['fields']
            upload_url = response['url']
            
            return upload_url, expires_at
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro ao gerar presigned URL: {e}")
            raise BusinessRuleViolationError(f"Falha ao gerar URL de upload: {str(e)}")
    
    async def download_file(self, s3_key: S3Key, local_path: str) -> bool:
        """
        Baixa arquivo do S3 para caminho local
        
        Returns:
            bool: True se sucesso, False se falha
        """
        try:
            async with await self._get_async_client() as client:
                await client.download_file(
                    s3_key.bucket,
                    s3_key.key,
                    local_path
                )
            
            logger.info(f"Arquivo baixado: {s3_key.key} -> {local_path}")
            return True
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro ao baixar arquivo {s3_key.key}: {e}")
            return False
    
    async def download_file_content(self, s3_key: S3Key) -> Optional[bytes]:
        """
        Baixa conteúdo do arquivo do S3 em memória
        
        Returns:
            bytes: Conteúdo do arquivo ou None se erro
        """
        try:
            async with await self._get_async_client() as client:
                response = await client.get_object(
                    Bucket=s3_key.bucket,
                    Key=s3_key.key
                )
                
                content = await response['Body'].read()
                
            logger.info(f"Conteúdo baixado: {s3_key.key} ({len(content)} bytes)")
            return content
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro ao baixar conteúdo {s3_key.key}: {e}")
            return None
    
    async def delete_file(self, s3_key: S3Key) -> bool:
        """
        Deleta arquivo do S3
        
        Returns:
            bool: True se sucesso, False se falha
        """
        try:
            async with await self._get_async_client() as client:
                await client.delete_object(
                    Bucket=s3_key.bucket,
                    Key=s3_key.key
                )
            
            logger.info(f"Arquivo deletado: {s3_key.key}")
            return True
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro ao deletar arquivo {s3_key.key}: {e}")
            return False
    
    async def file_exists(self, s3_key: S3Key) -> bool:
        """
        Verifica se arquivo existe no S3
        
        Returns:
            bool: True se existe, False se não existe
        """
        try:
            async with await self._get_async_client() as client:
                await client.head_object(
                    Bucket=s3_key.bucket,
                    Key=s3_key.key
                )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Erro ao verificar arquivo {s3_key.key}: {e}")
            return False
        except BotoCoreError as e:
            logger.error(f"Erro ao verificar arquivo {s3_key.key}: {e}")
            return False
    
    async def get_file_size(self, s3_key: S3Key) -> Optional[int]:
        """
        Obtém tamanho do arquivo no S3
        
        Returns:
            int: Tamanho em bytes ou None se erro
        """
        try:
            async with await self._get_async_client() as client:
                response = await client.head_object(
                    Bucket=s3_key.bucket,
                    Key=s3_key.key
                )
                
            return response['ContentLength']
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro ao obter tamanho {s3_key.key}: {e}")
            return None
    
    async def cleanup_temp_files(self, prefix: str = "temp/", older_than_hours: int = 24) -> int:
        """
        Remove arquivos temporários antigos
        
        Args:
            prefix: Prefixo dos arquivos temporários
            older_than_hours: Remover arquivos mais antigos que X horas
            
        Returns:
            int: Número de arquivos removidos
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
            deleted_count = 0
            
            async with await self._get_async_client() as client:
                # Listar objetos com prefixo
                paginator = client.get_paginator('list_objects_v2')
                
                async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                    if 'Contents' not in page:
                        continue
                    
                    for obj in page['Contents']:
                        # Verificar se é mais antigo que o limite
                        if obj['LastModified'].replace(tzinfo=None) < cutoff_time:
                            s3_key = S3Key(bucket=self.bucket, key=obj['Key'], region=self.region)
                            
                            if await self.delete_file(s3_key):
                                deleted_count += 1
            
            logger.info(f"Cleanup S3: {deleted_count} arquivos temporários removidos")
            return deleted_count
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro no cleanup S3: {e}")
            return 0
    
    async def test_connection(self) -> bool:
        """
        Testa conexão com S3
        
        Returns:
            bool: True se conectado, False se erro
        """
        try:
            async with await self._get_async_client() as client:
                # Tentar listar buckets ou fazer head_bucket
                await client.head_bucket(Bucket=self.bucket)
            
            logger.info(f"Conexão S3 OK: bucket '{self.bucket}' acessível")
            return True
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erro na conexão S3: {e}")
            return False
