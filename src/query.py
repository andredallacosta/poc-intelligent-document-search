import os
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

class DocumentQuery:
    def __init__(self, db_path="./data/chroma_db"):
        load_dotenv()
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY"))
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.db = Chroma(
            collection_name="documents",
            client=client,
            persist_directory=db_path,
            embedding_function=self.embeddings
        )
    
    def search(self, query, n_results=5, filters=None):
        docs_scores = self.db.similarity_search_with_relevance_scores(
            query,
            k=n_results,
            filter=filters
        )
        return self._format_results(docs_scores)
    
    def _format_results(self, docs_scores):
        formatted = []
        for doc, score in docs_scores:
            formatted.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "distance": 1 - float(score),
                "id": doc.metadata.get("id")
            })
        return formatted

if __name__ == "__main__":
    query = DocumentQuery()
    
    search_term = input("Digite sua pergunta: ")
    results = query.search(search_term, n_results=5)
    
    print(f"\nResultados para: '{search_term}'\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Fonte: {result['metadata'].get('source', 'N/A')}")
        print(f"   Similaridade: {1 - result['distance']:.3f}")
        print(f"   Texto: {result['text'][:200]}...")
        print("-" * 50)

        with open("results.txt", "a") as f:
            f.write(f"{i}. Fonte: {result['metadata'].get('source', 'N/A')}\n")
            f.write(f"   Similaridade: {1 - result['distance']:.3f}\n")
            f.write(f"   Texto: {result['text']}...\n")
            f.write("-" * 50 + "\n")
