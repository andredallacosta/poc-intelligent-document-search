from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

class Chunker:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._tiktoken_len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _tiktoken_len(self, text):
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text, metadata):
        chunks = self.splitter.split_text(text)
        
        chunked_data = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = f"{metadata.get('source', 'unknown')}_{i}"
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            
            chunked_data.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
        
        return chunked_data
