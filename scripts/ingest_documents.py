#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.config.settings import settings
from infrastructure.processors.text_chunker import TextChunker
from infrastructure.external.openai_client import OpenAIClient
from interface.dependencies.container import container
from domain.value_objects.document_metadata import DocumentMetadata
from domain.services.document_service import DocumentService


async def extract_text_from_file(file_path: Path) -> str:
    """Extract text from various file formats"""
    try:
        if file_path.suffix.lower() == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file_path.suffix.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            print(f"Unsupported file format: {file_path.suffix}")
            return ""
            
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""


async def process_document(file_path: Path, document_service: DocumentService) -> bool:
    """Process a single document"""
    try:
        print(f"Processing: {file_path.name}")
        
        # Extract text
        content = await extract_text_from_file(file_path)
        if not content.strip():
            print(f"No content extracted from {file_path.name}")
            return False
        
        # Create metadata
        stat = file_path.stat()
        metadata = DocumentMetadata(
            source=str(file_path),
            file_size=stat.st_size,
            file_type=file_path.suffix.lower().lstrip('.'),
            title=file_path.stem,
            word_count=len(content.split())
        )
        
        # Check if already exists
        existing = await document_service.get_document_by_source(str(file_path))
        if existing:
            print(f"Document already exists: {file_path.name}")
            return False
        
        # Create document
        document = await document_service.create_document(
            title=file_path.stem,
            content=content,
            file_path=str(file_path),
            metadata=metadata
        )
        
        # Process chunks and embeddings
        chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            use_contextual_retrieval=settings.use_contextual_retrieval
        )
        
        chunks = chunker.chunk_document_content(
            content=content,
            document_id=str(document.id),
            metadata=metadata.to_dict() if hasattr(metadata, 'to_dict') else {}
        )
        
        # Add chunks to document
        await document_service.add_chunks_to_document(document.id, chunks)
        
        # Generate and store embeddings
        openai_client = container.get_openai_client()
        vector_repo = container.get_vector_repository()
        
        for chunk in chunks:
            embedding = await openai_client.generate_embedding(chunk.content)
            await vector_repo.add_chunk_embedding(
                chunk_id=chunk.id,
                embedding=embedding,
                metadata={
                    "document_id": str(document.id),
                    "chunk_index": chunk.chunk_index,
                    "source": metadata.source
                }
            )
        
        print(f"✅ Processed: {file_path.name} ({len(chunks)} chunks)")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")
        return False


async def ingest_documents_from_directory(directory: Path) -> None:
    """Ingest all documents from a directory"""
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return
    
    # Get document service with proper DI
    document_repo = container.get_document_repository()
    document_service = DocumentService(document_repo)
    
    # Find all supported files
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
    files = []
    
    for ext in supported_extensions:
        files.extend(directory.glob(f"**/*{ext}"))
    
    if not files:
        print(f"No supported documents found in {directory}")
        return
    
    print(f"Found {len(files)} documents to process")
    
    # Process each file
    success_count = 0
    for file_path in files:
        success = await process_document(file_path, document_service)
        if success:
            success_count += 1
    
    print(f"\n✅ Completed: {success_count}/{len(files)} documents processed")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents into the system")
    parser.add_argument(
        "--directory", 
        type=Path, 
        default=Path("./documents"),
        help="Directory containing documents to ingest"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Single file to ingest"
    )
    
    args = parser.parse_args()
    
    if args.file:
        if args.file.exists():
            document_repo = container.get_document_repository()
            document_service = DocumentService(document_repo)
            asyncio.run(process_document(args.file, document_service))
        else:
            print(f"File not found: {args.file}")
    else:
        asyncio.run(ingest_documents_from_directory(args.directory))


if __name__ == "__main__":
    main()
