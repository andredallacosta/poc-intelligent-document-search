import os
import uuid
from pathlib import Path
import chromadb
from chromadb.config import Settings
import pdfplumber
from docx import Document
import trafilatura
from embedder import Embedder
from chunker import Chunker

class DocumentIngestor:
    def __init__(self, db_path="./data/chroma_db"):
        self.db_path = db_path
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.embedder = Embedder()
        self.chunker = Chunker()
    
    def parse_pdf(self, file_path):
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    texts.append(t)
        text = "\n\n".join(texts)
        metadata = {
            "source": os.path.basename(file_path),
            "file_type": "pdf",
            "file_path": file_path
        }
        return text, metadata
    
    def parse_docx(self, file_path):
        try:
            doc = Document(file_path)
            text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            
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
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        
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
        embeddings = self.embedder.embed_chunks(chunks)
        
        self._store_embeddings(embeddings)
        
        return len(chunks)
    
    def ingest_url(self, url):
        text, metadata = self.parse_url(url)
        chunks = self.chunker.chunk_text(text, metadata)
        embeddings = self.embedder.embed_chunks(chunks)
        
        self._store_embeddings(embeddings)
        
        return len(chunks)
    
    def _store_embeddings(self, embeddings):
        ids = []
        vectors = []
        metadatas = []
        documents = []
        
        for emb in embeddings:
            ids.append(str(uuid.uuid4()))
            vectors.append(emb["embedding"])
            metadatas.append(emb["metadata"])
            documents.append(emb["text"])
        
        self.collection.add(
            embeddings=vectors,
            metadatas=metadatas,
            documents=documents,
            ids=ids
        )

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
