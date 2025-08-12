import os
import hashlib
from pathlib import Path
from chromadb.config import Settings
from langchain_community.document_loaders import PDFPlumberLoader, Docx2txtLoader, WebBaseLoader
from langchain_chroma import Chroma
from embedder import Embedder
from chunker import Chunker

class DocumentIngestor:
    def __init__(self, db_path="./data/chroma_db"):
        self.db_path = db_path
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.embedder = Embedder()
        self.chunker = Chunker()
        self.db = Chroma(
            collection_name="documents",
            persist_directory=db_path,
            embedding_function=self.embedder.embeddings,
            client_settings=Settings(anonymized_telemetry=False)
        )
    
    def parse_pdf(self, file_path):
        loader = PDFPlumberLoader(file_path)
        doc = loader.load()
        text = "\n\n".join(d.page_content for d in doc if d.page_content)
        metadata = {
            "source": os.path.basename(file_path),
            "file_type": "pdf",
            "file_path": file_path,
        }
        return text, metadata
    
    def parse_docx(self, file_path):
        try:
            doc = Docx2txtLoader(file_path).load()
            text = "\n\n".join(d.page_content for d in doc if d.page_content)
            if not text.strip():
                raise ValueError("Documento DOCX vazio ou sem texto")
            metadata = {
                "source": os.path.basename(file_path),
                "file_type": "docx",
                "file_path": file_path
            }
            return text, metadata
        except Exception as e:
            raise Exception(f"Erro ao processar DOCX {file_path}: {e}")
    
    def parse_url(self, url):
        doc = WebBaseLoader(urls=[url]).load()
        text = "\n\n".join(d.page_content for d in doc if d.page_content)
        if not text:
            raise ValueError(f"Não foi possível extrair conteúdo da URL: {url}")
        metadata = {
            "source": url,
            "file_type": "url",
            "url": url
        }
        return text, metadata
    
    def ingest_file(self, file_path):
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            text, metadata = self.parse_pdf(str(file_path))
        elif file_path.suffix.lower() == '.docx':
            text, metadata = self.parse_docx(str(file_path))
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {file_path.suffix}")
        
        chunks = self.chunker.chunk_text(text, metadata)
        chunks = self._assign_chunk_ids(chunks)
        chunks = self._filter_existing_chunks(chunks)
        if not chunks:
            return 0
        for c in chunks:
            c["metadata"]["id"] = c["id"]
        self.db.add_texts(
            texts=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks]
        )
        
        return len(chunks)
    
    def ingest_url(self, url):
        text, metadata = self.parse_url(url)
        chunks = self.chunker.chunk_text(text, metadata)
        chunks = self._assign_chunk_ids(chunks)
        chunks = self._filter_existing_chunks(chunks)
        if not chunks:
            return 0
        for c in chunks:
            c["metadata"]["id"] = c["id"]
        self.db.add_texts(
            texts=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks]
        )
        
        return len(chunks)

    def _assign_chunk_ids(self, chunks):
        assigned = []
        for chunk in chunks:
            metadata = chunk["metadata"]
            source = metadata.get("source", "unknown")
            index = metadata.get("chunk_index")
            text = chunk["text"]
            base = f"{source}|{index}|{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
            chunk_with_id = {
                **chunk,
                "id": base
            }
            assigned.append(chunk_with_id)
        return assigned

    def _filter_existing_chunks(self, chunks):
        if not chunks:
            return []
        ids = [c["id"] for c in chunks]
        try:
            existing = self.db.get(ids=ids)
            existing_ids = set(existing.get("ids", [])) if existing else set()
        except Exception:
            existing_ids = set()
        return [c for c in chunks if c["id"] not in existing_ids]

if __name__ == "__main__":
    ingestor = DocumentIngestor()
    
    documents_dir = Path("./documents")
    if documents_dir.exists():
        for file_path in documents_dir.glob("*"):
            if file_path.suffix.lower() in ['.pdf', '.docx']:
                try:
                    chunks = ingestor.ingest_file(file_path)
                    print(f"Processado {file_path.name}: {chunks} chunks")
                except Exception as e:
                    print(f"Erro ao processar {file_path.name}: {e}")
    else:
        print("Pasta documents/ não encontrada")
