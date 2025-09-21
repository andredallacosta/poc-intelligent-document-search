from enum import Enum


class ProcessingStatus(Enum):
    """Status do processamento de documentos"""
    
    UPLOADED = "uploaded"           # Upload concluído, aguardando processamento
    EXTRACTING = "extracting"       # Extraindo texto do documento
    CHECKING_DUPLICATES = "checking_duplicates"  # Verificando duplicatas
    CHUNKING = "chunking"           # Dividindo em chunks
    EMBEDDING = "embedding"         # Gerando embeddings
    COMPLETED = "completed"         # Processamento concluído com sucesso
    FAILED = "failed"              # Falha no processamento
    DUPLICATE = "duplicate"         # Documento duplicado detectado
    
    @property
    def is_final(self) -> bool:
        """Verifica se é um status final (não muda mais)"""
        return self in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.DUPLICATE
        ]
    
    @property
    def is_processing(self) -> bool:
        """Verifica se está em processamento"""
        return self in [
            ProcessingStatus.EXTRACTING,
            ProcessingStatus.CHECKING_DUPLICATES,
            ProcessingStatus.CHUNKING,
            ProcessingStatus.EMBEDDING
        ]
    
    @property
    def progress_percentage(self) -> int:
        """Retorna porcentagem de progresso estimada"""
        progress_map = {
            ProcessingStatus.UPLOADED: 5,
            ProcessingStatus.EXTRACTING: 25,
            ProcessingStatus.CHECKING_DUPLICATES: 35,
            ProcessingStatus.CHUNKING: 55,
            ProcessingStatus.EMBEDDING: 85,
            ProcessingStatus.COMPLETED: 100,
            ProcessingStatus.FAILED: 0,
            ProcessingStatus.DUPLICATE: 100,
        }
        return progress_map.get(self, 0)
    
    @property
    def description(self) -> str:
        """Retorna descrição amigável do status"""
        descriptions = {
            ProcessingStatus.UPLOADED: "Arquivo enviado, iniciando processamento...",
            ProcessingStatus.EXTRACTING: "Extraindo texto do documento...",
            ProcessingStatus.CHECKING_DUPLICATES: "Verificando se documento já existe...",
            ProcessingStatus.CHUNKING: "Dividindo documento em seções...",
            ProcessingStatus.EMBEDDING: "Gerando embeddings para busca...",
            ProcessingStatus.COMPLETED: "Processamento concluído com sucesso",
            ProcessingStatus.FAILED: "Falha no processamento",
            ProcessingStatus.DUPLICATE: "Documento já existe na base de conhecimento",
        }
        return descriptions.get(self, "Status desconhecido")
