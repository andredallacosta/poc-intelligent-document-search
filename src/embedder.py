import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

class Embedder:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY"))
    
    def embed_text(self, text):
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            raise Exception(f"Erro ao gerar embedding: {e}")
    
    def embed_chunks(self, chunks):
        texts = [c["text"] for c in chunks]
        vectors = self.embeddings.embed_documents(texts)
        results = []
        for i, chunk in enumerate(chunks):
            results.append({
                "id": chunk.get("id"),
                "embedding": vectors[i],
                "metadata": chunk["metadata"],
                "text": chunk["text"]
            })
        return results
