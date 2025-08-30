import sys
import os
import subprocess
import json
import tempfile
from typing import List, Optional, Dict, Any
import logging

from api.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        try:
            logger.info("Initializing RAG service using subprocess method")
            self.query_script_path = os.path.join(os.path.dirname(__file__), '../../src/query.py')
            logger.info(f"Query script path: {self.query_script_path}")
            
            # Test if script exists
            if not os.path.exists(self.query_script_path):
                raise FileNotFoundError(f"Query script not found: {self.query_script_path}")
                
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    async def search_documents(
        self, 
        query: str, 
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Searching documents for query: '{query[:100]}...' using subprocess")
            
            # Call the original query script as subprocess
            # Use the same Python from venv
            python_path = sys.executable or "python"
            cmd = [
                python_path, 
                self.query_script_path, 
                query, 
                str(n_results)
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Set working directory to project root
            project_root = os.path.join(os.path.dirname(self.query_script_path), '..')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                env=dict(os.environ, PYTHONPATH=project_root)
            )
            
            if result.returncode != 0:
                logger.error(f"Query script failed: {result.stderr}")
                raise Exception(f"Query script error: {result.stderr}")
            
            # Parse JSON output
            try:
                formatted_results = json.loads(result.stdout)
                logger.info(f"Found {len(formatted_results)} results")
                return formatted_results
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse query output: {result.stdout}")
                raise Exception(f"JSON decode error: {e}")
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    def get_context_for_llm(self, search_results: List[Dict[str, Any]]) -> str:
        if not search_results:
            return ""
        
        context_parts = []
        for i, result in enumerate(search_results[:5], 1):
            source = result.get("source", "Unknown")
            text = result.get("text", "")
            similarity = result.get("similarity", 0)
            
            context_part = f"[Fonte {i}: {source} (Similaridade: {similarity:.2f})]\n{text}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)

rag_service = RAGService()
