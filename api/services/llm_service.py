import os
import time
from typing import List, Dict, Any, Optional
import logging
from openai import OpenAI
from dotenv import load_dotenv

from api.core.config import settings

load_dotenv()
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4o-mini"
            logger.info("LLM service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        return """Você é um assistente especializado em gestão pública e redação oficial no Brasil.

Suas responsabilidades:
- Responder perguntas sobre documentos oficiais, ofícios, gestão municipal
- Usar SEMPRE as informações dos documentos fornecidos como contexto
- Citar as fontes dos documentos quando relevante
- Dar respostas práticas e aplicáveis à gestão pública brasileira
- Usar linguagem formal mas acessível

Diretrizes:
- SEMPRE mencione de quais documentos você retirou a informação
- Se não souber algo baseado nos documentos, diga claramente
- Forneça exemplos práticos quando possível
- Mantenha o foco na gestão pública municipal"""

    def _build_context_from_sources(self, search_results: List[Dict[str, Any]]) -> str:
        if not search_results:
            return "Nenhum documento relevante encontrado."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            source = result.get("source", "Documento desconhecido")
            text = result.get("text", "")
            similarity = result.get("similarity", 0)
            
            context_part = f"""
=== DOCUMENTO {i} ===
Fonte: {source}
Relevância: {similarity:.1%}
Conteúdo: {text}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)

    async def generate_response(
        self,
        user_message: str,
        search_results: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            
            # System prompt
            messages.append({
                "role": "system",
                "content": self._build_system_prompt()
            })
            
            # Context from documents
            context = self._build_context_from_sources(search_results)
            messages.append({
                "role": "system",
                "content": f"DOCUMENTOS PARA CONTEXTO:\n{context}"
            })
            
            # Conversation history
            if conversation_history:
                messages.extend(conversation_history[-8:])  # Last 8 messages
            
            # Current user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Count tokens (rough estimate)
            total_tokens_estimate = sum(len(msg["content"].split()) * 1.3 for msg in messages)
            
            if total_tokens_estimate > settings.max_tokens_per_request:
                # Truncate conversation history if too long
                messages = messages[:2] + messages[-2:]  # Keep system + last exchange
            
            logger.info(f"Sending {len(messages)} messages to GPT-4o-mini")
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Extract response
            assistant_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Extract sources mentioned
            sources_used = []
            for result in search_results:
                source = result.get("source", "")
                if source and (source.lower() in assistant_message.lower() or 
                              any(word in assistant_message.lower() for word in source.lower().split())):
                    sources_used.append({
                        "source": source,
                        "similarity": result.get("similarity", 0),
                        "preview": result.get("preview", "")
                    })
            
            logger.info(f"Generated response in {response_time}ms, {tokens_used} tokens")
            
            return {
                "response": assistant_message,
                "tokens_used": tokens_used,
                "response_time_ms": response_time,
                "sources_used": sources_used,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

llm_service = LLMService()

