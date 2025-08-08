import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class Embedder:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
    
    def embed_text(self, text):
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Erro ao gerar embedding: {e}")
    
    def embed_chunks(self, chunks):
        embeddings = []
        for chunk in chunks:
            embedding = self.embed_text(chunk["text"])
            embeddings.append({
                "embedding": embedding,
                "metadata": chunk["metadata"],
                "text": chunk["text"]
            })
        return embeddings
