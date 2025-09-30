import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.file_upload import FileUpload
from domain.repositories.file_upload_repository import FileUploadRepository
from domain.value_objects.s3_key import S3Key
from infrastructure.database.models import FileUploadModel

logger = logging.getLogger(__name__)


class PostgresFileUploadRepository(FileUploadRepository):
    """Implementação PostgreSQL do repositório de FileUpload"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, file_upload: FileUpload) -> None:
        """Salva um FileUpload"""
        try:
            stmt = select(FileUploadModel).where(FileUploadModel.id == file_upload.id)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.filename = file_upload.filename
                existing.file_size = file_upload.file_size
                existing.content_type = file_upload.content_type
                existing.s3_bucket = (
                    file_upload.s3_key.bucket if file_upload.s3_key else None
                )
                existing.s3_key = file_upload.s3_key.key if file_upload.s3_key else None
                existing.s3_region = (
                    file_upload.s3_key.region if file_upload.s3_key else None
                )
                existing.upload_url = file_upload.upload_url
                existing.expires_at = file_upload.expires_at
                existing.uploaded_at = file_upload.uploaded_at
            else:
                model = FileUploadModel(
                    id=file_upload.id,
                    document_id=file_upload.document_id,
                    filename=file_upload.filename,
                    file_size=file_upload.file_size,
                    content_type=file_upload.content_type,
                    s3_bucket=file_upload.s3_key.bucket if file_upload.s3_key else None,
                    s3_key=file_upload.s3_key.key if file_upload.s3_key else None,
                    s3_region=file_upload.s3_key.region if file_upload.s3_key else None,
                    upload_url=file_upload.upload_url,
                    expires_at=file_upload.expires_at,
                    uploaded_at=file_upload.uploaded_at,
                    created_at=file_upload.created_at,
                )
                self.session.add(model)

            await self.session.commit()
            logger.info(f"FileUpload salvo: {file_upload.id} - {file_upload.filename}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erro ao salvar FileUpload {file_upload.id}: {e}")
            raise

    async def find_by_id(self, upload_id: UUID) -> Optional[FileUpload]:
        """Busca FileUpload por ID"""
        try:
            stmt = select(FileUploadModel).where(FileUploadModel.id == upload_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error(f"Erro ao buscar FileUpload {upload_id}: {e}")
            return None

    async def find_by_document_id(self, document_id: UUID) -> Optional[FileUpload]:
        """Busca FileUpload por document_id"""
        try:
            stmt = select(FileUploadModel).where(
                FileUploadModel.document_id == document_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error(
                f"Erro ao buscar FileUpload por document_id {document_id}: {e}"
            )
            return None

    async def delete(self, upload_id: UUID) -> bool:
        """Remove FileUpload"""
        try:
            stmt = delete(FileUploadModel).where(FileUploadModel.id == upload_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"FileUpload removido: {upload_id}")

            return deleted

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erro ao remover FileUpload {upload_id}: {e}")
            return False

    def _model_to_entity(self, model: FileUploadModel) -> FileUpload:
        """Converte model SQLAlchemy para entidade de domínio"""
        s3_key = None
        if model.s3_bucket and model.s3_key:
            s3_key = S3Key(
                bucket=model.s3_bucket, key=model.s3_key, region=model.s3_region
            )

        file_upload = FileUpload(
            id=model.id,
            document_id=model.document_id,
            filename=model.filename,
            file_size=model.file_size,
            content_type=model.content_type,
            s3_key=s3_key,
            upload_url=model.upload_url,
            expires_at=model.expires_at,
            uploaded_at=model.uploaded_at,
            created_at=model.created_at,
        )

        return file_upload
