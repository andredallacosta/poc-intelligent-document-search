import chromadb
from chromadb.config import Settings
from embedder import Embedder

class DocumentQuery:
    def __init__(self, db_path="./data/chroma_db"):
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_collection(name="documents")
        self.embedder = Embedder()
    
    def search(self, query, n_results=5, filters=None):
        query_embedding = self.embedder.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filters
        )
        
        return self._format_results(results)
    
    def _format_results(self, results):
        formatted = []
        
        for i in range(len(results['documents'][0])):
            formatted.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i],
                "id": results['ids'][0][i]
            })
        
        return formatted

if __name__ == "__main__":
    query = DocumentQuery()
    
    search_term = input("Digite sua pergunta: ")
    results = query.search(search_term, n_results=3)
    
    print(f"\nResultados para: '{search_term}'\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Fonte: {result['metadata'].get('source', 'N/A')}")
        print(f"   Similaridade: {1 - result['distance']:.3f}")
        print(f"   Texto: {result['text'][:200]}...")
        print("-" * 50)
