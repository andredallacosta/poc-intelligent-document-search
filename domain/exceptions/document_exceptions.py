class DocumentError(Exception):
    pass


class DocumentNotFoundError(DocumentError):
    pass


class DocumentAlreadyExistsError(DocumentError):
    pass


class InvalidDocumentError(DocumentError):
    pass


class DocumentProcessingError(DocumentError):
    pass


class ChunkingError(DocumentError):
    pass


class EmbeddingError(DocumentError):
    pass
