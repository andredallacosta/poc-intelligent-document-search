from typing import Dict, List

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from domain.entities.document import DocumentChunk
from domain.exceptions.document_exceptions import ChunkingError
from infrastructure.processors.context_generator import ContextGenerator


class TextChunker:

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        use_contextual_retrieval: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_contextual_retrieval = use_contextual_retrieval

        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            raise ChunkingError(f"Failed to initialize tiktoken encoding: {e}")

        self.context_generator = (
            ContextGenerator() if use_contextual_retrieval else None
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._tiktoken_len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _tiktoken_len(self, text: str) -> int:
        try:
            return len(self.encoding.encode(text))
        except Exception:
            return len(text.split())

    def chunk_document_content(
        self, content: str, document_id: str, metadata: Dict
    ) -> List[DocumentChunk]:
        try:
            if self.use_contextual_retrieval and self.context_generator:
                enhanced_metadata = self.context_generator.extract_document_metadata(
                    content, metadata
                )
            else:
                enhanced_metadata = metadata.copy()

            text_chunks = self.splitter.split_text(content)

            document_chunks = []
            start_char = 0

            for i, chunk_text in enumerate(text_chunks):
                end_char = start_char + len(chunk_text)

                chunk_metadata = enhanced_metadata.copy()
                chunk_metadata.update(
                    {
                        "chunk_id": f"{document_id}_{i}",
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                    }
                )

                if self.use_contextual_retrieval and self.context_generator:
                    position_info = {
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "relative_position": (
                            i / len(text_chunks) if len(text_chunks) > 1 else 0
                        ),
                    }

                    contextualized_text = self.context_generator.generate_context(
                        chunk_text, enhanced_metadata, position_info
                    )
                else:
                    contextualized_text = chunk_text

                chunk = DocumentChunk(
                    id=None,
                    document_id=document_id,
                    content=contextualized_text,
                    original_content=chunk_text,
                    chunk_index=i,
                    start_char=start_char,
                    end_char=end_char,
                )

                document_chunks.append(chunk)
                start_char = end_char

            return document_chunks

        except Exception as e:
            raise ChunkingError(f"Failed to chunk document content: {e}")

    def estimate_chunk_count(self, content: str) -> int:
        token_count = self._tiktoken_len(content)
        return max(1, (token_count + self.chunk_size - 1) // self.chunk_size)
