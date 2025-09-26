#!/usr/bin/env python3

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any

import aiohttp


class RealDocumentTester:
    """Testa ingestão usando documentos reais da pasta /documents"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.documents_dir = Path("documents")
        self.supported_extensions = {".pdf", ".docx", ".doc"}
        
    def get_real_documents(self) -> List[Path]:
        """Obtém lista de documentos reais para testar"""
        documents = []
        
        if not self.documents_dir.exists():
            print(f"❌ Pasta {self.documents_dir} não encontrada")
            return documents
        
        for file_path in self.documents_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                documents.append(file_path)
                continue
        
        return sorted(documents)
    
    def get_content_type(self, file_path: Path) -> str:
        """Retorna content-type baseado na extensão"""
        extension = file_path.suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword"
        }
        return content_types.get(extension, "application/octet-stream")
    
    def extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extrai metadados do documento baseado no nome"""
        filename = file_path.stem
        
        # Detectar tipo de documento baseado no nome
        if "manual" in filename.lower() and "redação" in filename.lower():
            return {
                "title": "Manual de Redação Oficial 2ª Edição",
                "description": "Manual completo de redação oficial para órgãos públicos",
                "tags": ["manual", "redação", "oficial", "governo", "normas"]
            }
        elif "ofício" in filename.lower():
            if "vereador" in filename.lower():
                return {
                    "title": f"Modelo de Ofício - Vereadores ({filename})",
                    "description": "Modelo de ofício para comunicação com vereadores",
                    "tags": ["ofício", "vereador", "modelo", "comunicação"]
                }
            elif "prefeitura" in filename.lower():
                return {
                    "title": f"Modelo de Ofício - Prefeitura ({filename})",
                    "description": "Modelo de ofício para comunicação oficial da prefeitura",
                    "tags": ["ofício", "prefeitura", "modelo", "oficial"]
                }
            else:
                return {
                    "title": f"Modelo de Ofício ({filename})",
                    "description": "Modelo de ofício para comunicação oficial",
                    "tags": ["ofício", "modelo", "comunicação", "oficial"]
                }
        elif "minuta" in filename.lower():
            return {
                "title": f"Minuta de Documento ({filename})",
                "description": "Minuta de documento oficial",
                "tags": ["minuta", "modelo", "documento"]
            }
        elif "links" in filename.lower() or "pdf" in filename.lower():
            return {
                "title": f"Lista de Referências ({filename})",
                "description": "Lista de links e referências para documentos PDF",
                "tags": ["referência", "links", "pdf", "leitura"]
            }
        else:
            return {
                "title": filename,
                "description": f"Documento: {filename}",
                "tags": ["documento", "oficial"]
            }
    
    async def upload_single_document(self, session: aiohttp.ClientSession, file_path: Path) -> Dict[str, Any]:
        """Faz upload de um documento específico"""
        
        print(f"\n📄 Processando: {file_path.name}")
        
        file_size = file_path.stat().st_size
        content_type = self.get_content_type(file_path)
        metadata = self.extract_document_metadata(file_path)
        
        print(f"   📊 Tamanho: {file_size:,} bytes")
        print(f"   📋 Tipo: {content_type}")
        print(f"   🏷️  Título: {metadata['title']}")
        
        try:
            # 1. Solicitar URL presigned
            presigned_payload = {
                "filename": file_path.name,
                "file_size": file_size,
                "content_type": content_type,
                **metadata
            }
            
            async with session.post(
                f"{self.api_base_url}/api/v1/documents/upload/presigned",
                json=presigned_payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"   ❌ Erro presigned URL: {resp.status} - {error_text}")
                    return {"success": False, "error": f"Presigned URL failed: {resp.status}"}
                
                presigned_data = await resp.json()
                document_id = presigned_data["document_id"]
                upload_url = presigned_data["upload_url"]
                upload_id = presigned_data["upload_id"]
                upload_fields = presigned_data["upload_fields"]
            
            print(f"   ✅ URL presigned obtida: {document_id}")
            
            # 2. Upload para S3 usando presigned POST
            with open(file_path, "rb") as file_obj:
                # Preparar dados para presigned POST
                form_data = aiohttp.FormData()
                
                # Adicionar campos obrigatórios primeiro
                for key, value in upload_fields.items():
                    form_data.add_field(key, value)
                
                # Adicionar arquivo por último
                form_data.add_field('file', file_obj.read(), 
                                  filename=os.path.basename(file_path), 
                                  content_type=content_type)
                
                async with session.post(upload_url, data=form_data) as resp:
                    if resp.status not in [200, 201, 204]:
                        error_text = await resp.text()
                        print(f"   ❌ Erro upload S3: {resp.status} - {error_text}")
                        return {"success": False, "error": f"S3 upload failed: {resp.status}"}
            
            print(f"   ✅ Upload S3 concluído")
            
            # 3. Solicitar processamento
            process_payload = {"upload_id": upload_id}
            
            async with session.post(
                f"{self.api_base_url}/api/v1/documents/{document_id}/process",
                json=process_payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"   ❌ Erro processamento: {resp.status} - {error_text}")
                    return {"success": False, "error": f"Processing failed: {resp.status}"}
                
                process_data = await resp.json()
                job_id = process_data["job_id"]
            
            print(f"   ✅ Processamento iniciado: {job_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "job_id": job_id,
                "filename": file_path.name,
                "title": metadata["title"],
                "file_size": file_size
            }
            
        except Exception as e:
            print(f"   ❌ Erro inesperado: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def monitor_processing_jobs(self, session: aiohttp.ClientSession, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Monitora progresso de múltiplos jobs"""
        
        print(f"\n🔄 Monitorando {len(jobs)} jobs de processamento...")
        
        completed_jobs = []
        pending_jobs = [job for job in jobs if job["success"]]
        max_attempts = 60  # 10 minutos máximo
        attempt = 0
        
        while pending_jobs and attempt < max_attempts:
            print(f"\n📊 Tentativa {attempt + 1}/{max_attempts} - {len(pending_jobs)} jobs pendentes")
            
            still_pending = []
            
            for job in pending_jobs:
                document_id = job["document_id"]
                filename = job["filename"]
                
                try:
                    async with session.get(
                        f"{self.api_base_url}/api/v1/documents/{document_id}/status"
                    ) as resp:
                        if resp.status != 200:
                            print(f"   ❌ {filename}: Erro ao verificar status")
                            still_pending.append(job)
                            continue
                        
                        status_data = await resp.json()
                        status = status_data["status"]
                        progress = status_data.get("progress", 0)
                        current_step = status_data.get("current_step", "unknown")
                        
                        if status == "completed":
                            print(f"   ✅ {filename}: Concluído!")
                            job.update({
                                "final_status": "completed",
                                "progress": 100,
                                "processing_time": attempt * 10  # aproximado
                            })
                            completed_jobs.append(job)
                        elif status == "failed":
                            error_msg = status_data.get("error", "Erro desconhecido")
                            print(f"   ❌ {filename}: Falhou - {error_msg}")
                            job.update({
                                "final_status": "failed",
                                "error": error_msg
                            })
                            completed_jobs.append(job)
                        else:
                            print(f"   🔄 {filename}: {status} ({progress}%) - {current_step}")
                            still_pending.append(job)
                
                except Exception as e:
                    print(f"   ❌ {filename}: Erro ao monitorar - {str(e)}")
                    still_pending.append(job)
            
            pending_jobs = still_pending
            
            if pending_jobs:
                attempt += 1
                await asyncio.sleep(10)  # Aguardar 10 segundos
        
        # Marcar jobs que não terminaram como timeout
        for job in pending_jobs:
            job.update({
                "final_status": "timeout",
                "error": "Processamento demorou mais que o esperado"
            })
            completed_jobs.append(job)
        
        return completed_jobs
    
    async def test_search_with_real_docs(self, session: aiohttp.ClientSession) -> None:
        """Testa busca usando termos relacionados aos documentos reais"""
        
        print(f"\n🔍 Testando busca com documentos reais...")
        
        search_queries = [
            "como escrever um ofício oficial",
            "manual de redação",
            "modelo de ofício para vereador",
            "comunicação oficial prefeitura",
            "normas de redação oficial",
            "estrutura de um ofício",
            "documentos oficiais governo"
        ]
        
        for query in search_queries:
            print(f"\n🔎 Consulta: '{query}'")
            
            try:
                search_payload = {
                    "message": query,
                    "session_id": None
                }
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/chat/ask",
                    json=search_payload
                ) as resp:
                    if resp.status != 200:
                        print(f"   ❌ Erro na busca: {resp.status}")
                        continue
                    
                    search_data = await resp.json()
                    sources = search_data.get("sources", [])
                    answer = search_data.get("answer", "")
                    
                    print(f"   📚 {len(sources)} fontes encontradas")
                    print(f"   💬 Resposta: {answer[:100]}...")
                    
                    if sources:
                        print("   📄 Documentos relevantes:")
                        for i, source in enumerate(sources[:3], 1):
                            title = source.get("title", "Sem título")
                            print(f"      {i}. {title}")
            
            except Exception as e:
                print(f"   ❌ Erro na busca: {str(e)}")
            
            await asyncio.sleep(1)  # Pausa entre consultas
    
    async def run_full_test(self) -> None:
        """Executa teste completo com documentos reais"""
        
        print("🚀 Teste de Ingestão com Documentos Reais")
        print("=" * 50)
        
        # Verificar documentos disponíveis
        documents = self.get_real_documents()
        
        if not documents:
            print("❌ Nenhum documento encontrado na pasta /documents")
            print("💡 Certifique-se que a pasta contém arquivos PDF, DOC ou DOCX")
            return
        
        print(f"📁 Encontrados {len(documents)} documentos:")
        for doc in documents:
            size_mb = doc.stat().st_size / (1024 * 1024)
            print(f"   📄 {doc.name} ({size_mb:.1f} MB)")
        
        # Verificar se API está rodando
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.api_base_url}/health") as resp:
                    if resp.status != 200:
                        print(f"❌ API não está respondendo: {resp.status}")
                        return
                    print("✅ API está rodando")
            except Exception as e:
                print(f"❌ Erro ao conectar com API: {e}")
                return
            
            # Upload de todos os documentos
            print(f"\n📤 Iniciando upload de {len(documents)} documentos...")
            
            upload_jobs = []
            for doc in documents:
                job_result = await self.upload_single_document(session, doc)
                upload_jobs.append(job_result)
                await asyncio.sleep(1)  # Pausa entre uploads
            
            # Contar sucessos e falhas
            successful_uploads = [job for job in upload_jobs if job["success"]]
            failed_uploads = [job for job in upload_jobs if not job["success"]]
            
            print(f"\n📊 Resultado dos uploads:")
            print(f"   ✅ Sucessos: {len(successful_uploads)}")
            print(f"   ❌ Falhas: {len(failed_uploads)}")
            
            if failed_uploads:
                print("   💥 Falhas detalhadas:")
                for job in failed_uploads:
                    print(f"      - {job.get('filename', 'unknown')}: {job.get('error', 'unknown')}")
            
            if not successful_uploads:
                print("❌ Nenhum documento foi enviado com sucesso")
                return
            
            # Monitorar processamento
            completed_jobs = await self.monitor_processing_jobs(session, successful_uploads)
            
            # Estatísticas finais
            completed_success = [job for job in completed_jobs if job.get("final_status") == "completed"]
            completed_failed = [job for job in completed_jobs if job.get("final_status") == "failed"]
            completed_timeout = [job for job in completed_jobs if job.get("final_status") == "timeout"]
            
            print(f"\n📈 Resultado final do processamento:")
            print(f"   ✅ Processados com sucesso: {len(completed_success)}")
            print(f"   ❌ Falharam no processamento: {len(completed_failed)}")
            print(f"   ⏰ Timeout: {len(completed_timeout)}")
            
            if completed_success:
                print("\n🎉 Documentos processados com sucesso:")
                for job in completed_success:
                    title = job.get("title", job.get("filename", "unknown"))
                    size_kb = job.get("file_size", 0) / 1024
                    processing_time = job.get("processing_time", 0)
                    print(f"   📄 {title} ({size_kb:.1f} KB) - {processing_time}s")
                
                # Testar busca apenas se houver documentos processados
                await self.test_search_with_real_docs(session)
            
            print(f"\n🏁 Teste concluído!")
            print(f"   📤 {len(successful_uploads)} uploads realizados")
            print(f"   ✅ {len(completed_success)} documentos processados")
            print(f"   🔍 Busca testada com {len(completed_success)} documentos")


async def main():
    """Função principal"""
    tester = RealDocumentTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
