import logging
import tempfile
from pathlib import Path
from typing import Optional

from domain.entities.document import Document
from domain.entities.document_processing_job import DocumentProcessingJob
from domain.entities.file_upload import FileUpload
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.document_repository import DocumentRepository
from domain.repositories.vector_repository import VectorRepository
from domain.services.document_service import DocumentService
from domain.value_objects.content_hash import ContentHash
from domain.value_objects.document_metadata import DocumentMetadata
from domain.value_objects.processing_status import ProcessingStatus
from infrastructure.external.openai_client import OpenAIClient
from infrastructure.external.s3_service import S3Service
from infrastructure.processors.text_chunker import TextChunker

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Serviço de domínio para processar documentos completos"""

    def __init__(
        self,
        document_service: DocumentService,
        vector_repository: VectorRepository,
        text_chunker: TextChunker,
        openai_client: OpenAIClient,
        s3_service: S3Service,
        document_repository: DocumentRepository,
    ):
        self.document_service = document_service
        self.vector_repository = vector_repository
        self.text_chunker = text_chunker
        self.openai_client = openai_client
        self.s3_service = s3_service
        self.document_repository = document_repository

    async def process_uploaded_document(
        self, file_upload: FileUpload, job: DocumentProcessingJob
    ) -> Document:
        """
        Processa documento completo: download → extração → chunking → embeddings

        Returns:
            Document: Documento processado e salvo

        Raises:
            BusinessRuleViolationError: Se falha no processamento
        """
        try:
            job.update_status(ProcessingStatus.EXTRACTING, "Baixando arquivo do S3...")

            text_content = await self._download_and_extract_text(file_upload, job)

            job.update_status(
                ProcessingStatus.CHECKING_DUPLICATES,
                "Verificando se documento já existe...",
            )

            existing_document = await self._check_for_duplicate(
                text_content, job, file_upload
            )
            if existing_document:
                job.mark_as_duplicate(existing_document.id)
                await self._cleanup_s3_file(file_upload)
                return existing_document

            job.update_status(
                ProcessingStatus.CHUNKING, "Dividindo documento em seções..."
            )

            document = await self._create_document_with_chunks(
                file_upload, text_content, job
            )

            job.update_status(
                ProcessingStatus.EMBEDDING, "Gerando embeddings para busca..."
            )

            await self._generate_and_save_embeddings(document, job)

            job.update_status(
                ProcessingStatus.COMPLETED, "Processamento concluído com sucesso"
            )

            await self._cleanup_s3_file(file_upload)
            job.mark_s3_file_deleted()

            logger.info(f"Documento processado com sucesso: {document.id}")
            return document

        except Exception as e:
            logger.error(f"Erro no processamento do documento: {e}")
            job.fail_with_error(str(e))
            raise BusinessRuleViolationError(f"Falha no processamento: {str(e)}")

    async def _download_and_extract_text(
        self, file_upload: FileUpload, job: DocumentProcessingJob
    ) -> str:
        """Baixa arquivo do S3 e extrai texto"""
        if not file_upload.s3_key:
            raise BusinessRuleViolationError("S3 key não definida para o upload")

        with tempfile.NamedTemporaryFile(
            suffix=file_upload.file_extension, delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            success = await self.s3_service.download_file(file_upload.s3_key, tmp_path)
            if not success:
                raise BusinessRuleViolationError("Falha no download do S3")

            job.update_status(
                ProcessingStatus.EXTRACTING, "Extraindo texto do documento..."
            )

            if file_upload.is_pdf:
                text_content = await self._extract_text_from_pdf(tmp_path)
            elif file_upload.is_docx:
                text_content = await self._extract_text_from_docx(tmp_path)
            elif file_upload.is_doc:
                text_content = await self._extract_text_from_doc(tmp_path)
            else:
                raise BusinessRuleViolationError(
                    f"Tipo de arquivo não suportado: {file_upload.content_type}"
                )

            if not text_content or len(text_content.strip()) < 10:
                raise BusinessRuleViolationError(
                    "Documento não contém texto suficiente"
                )

            logger.info(f"Texto extraído: {len(text_content)} caracteres")
            return text_content

        finally:
            try:
                Path(tmp_path).unlink()
            except:
                pass

    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extrai texto de PDF usando PDFPlumberLoader"""
        try:
            from langchain_community.document_loaders import PDFPlumberLoader

            loader = PDFPlumberLoader(file_path)
            documents = loader.load()

            return "\n\n".join([doc.page_content for doc in documents])

        except Exception as e:
            logger.error(f"Erro na extração PDF: {e}")
            raise BusinessRuleViolationError(
                f"Falha na extração de texto PDF: {str(e)}"
            )

    async def _extract_text_from_docx(self, file_path: str) -> str:
        """Extrai texto de DOCX usando python-docx"""
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(file_path)
            paragraphs = [paragraph.text for paragraph in doc.paragraphs]

            return "\n\n".join(paragraphs)

        except Exception as e:
            logger.error(f"Erro na extração DOCX: {e}")
            raise BusinessRuleViolationError(
                f"Falha na extração de texto DOCX: {str(e)}"
            )

    async def _extract_text_from_doc(self, file_path: str) -> str:
        """Extrai texto de DOC legado usando docx2txt"""
        try:
            import docx2txt

            text = docx2txt.process(file_path)
            return text

        except Exception as e:
            logger.error(f"Erro na extração DOC: {e}")
            raise BusinessRuleViolationError(
                f"Falha na extração de texto DOC: {str(e)}"
            )

    async def _check_for_duplicate(
        self, text_content: str, job: DocumentProcessingJob, file_upload: FileUpload
    ) -> Optional[Document]:
        """Verifica se documento já existe baseado no hash do conteúdo OU filename"""
        try:
            content_hash = ContentHash.from_text(text_content)
            job.set_content_hash(content_hash)

            existing_by_content = await self.document_repository.find_by_content_hash(
                content_hash.value
            )
            if existing_by_content:
                logger.info(
                    f"Documento duplicado por conteúdo detectado: {existing_by_content.title}"
                )
                return existing_by_content

            existing_by_source = await self.document_repository.find_by_source(
                file_upload.filename
            )
            if existing_by_source:
                logger.info(
                    f"Documento duplicado por filename detectado: {existing_by_source.title}"
                )
                return existing_by_source

            return None

        except Exception as e:
            logger.warning(f"Erro na verificação de duplicata: {e}")
            return None

    async def _create_document_with_chunks(
        self, file_upload: FileUpload, text_content: str, job: DocumentProcessingJob
    ) -> Document:
        """Cria documento e chunks"""
        try:
            metadata = DocumentMetadata(
                source=file_upload.filename,
                file_size=file_upload.file_size,
                file_type=file_upload.content_type,
                custom_fields={
                    "upload_id": str(file_upload.id),
                    "content_hash": (
                        job.content_hash.value if job.content_hash else None
                    ),
                },
            )

            document = await self.document_service.create_document(
                title=file_upload.filename,
                content=text_content,
                file_path=file_upload.s3_key.full_path if file_upload.s3_key else "",
                metadata=metadata,
                skip_duplicate_check=True,
            )

            chunks = self.text_chunker.chunk_document_content(
                content=text_content,
                document_id=str(document.id),
                metadata={
                    "source": file_upload.filename,
                    "document_id": str(document.id),
                },
            )

            await self.document_service.add_chunks_to_document(document.id, chunks)

            job.update_chunks_progress(0, len(chunks))

            logger.info(f"Documento criado com {len(chunks)} chunks: {document.id}")
            return document

        except Exception as e:
            logger.error(f"Erro na criação de documento/chunks: {e}")
            raise BusinessRuleViolationError(f"Falha na criação do documento: {str(e)}")

    async def _generate_and_save_embeddings(
        self, document: Document, job: DocumentProcessingJob
    ) -> None:
        """Gera embeddings para todos os chunks do documento"""
        try:
            chunks = await self.document_service.get_document_chunks(document.id)

            if not chunks:
                raise BusinessRuleViolationError(
                    "Nenhum chunk encontrado para o documento"
                )

            batch_size = 20
            total_batches = (len(chunks) + batch_size - 1) // batch_size

            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i : i + batch_size]
                batch_number = (i // batch_size) + 1

                texts = [chunk.content for chunk in batch_chunks]
                embeddings = await self.openai_client.generate_embeddings_batch(texts)

                for chunk, embedding in zip(batch_chunks, embeddings):
                    await self.vector_repository.add_chunk_embedding(
                        chunk_id=chunk.id, embedding=embedding, metadata={}
                    )

                processed_count = min(i + batch_size, len(chunks))
                job.update_chunks_progress(processed_count, len(chunks))

                logger.info(
                    f"Batch {batch_number}/{total_batches} processado: {len(batch_chunks)} embeddings"
                )

            logger.info(
                f"Embeddings gerados para {len(chunks)} chunks do documento {document.id}"
            )

        except Exception as e:
            logger.error(f"Erro na geração de embeddings: {e}")
            raise BusinessRuleViolationError(
                f"Falha na geração de embeddings: {str(e)}"
            )

    async def _cleanup_s3_file(self, file_upload: FileUpload) -> None:
        """Remove arquivo do S3 após processamento"""
        if not file_upload.s3_key:
            return

        try:
            success = await self.s3_service.delete_file(file_upload.s3_key)
            if success:
                logger.info(f"Arquivo S3 removido: {file_upload.s3_key.key}")
            else:
                logger.warning(
                    f"Falha na remoção do arquivo S3: {file_upload.s3_key.key}"
                )
        except Exception as e:
            logger.error(f"Erro na limpeza S3: {e}")
