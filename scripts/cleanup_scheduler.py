#!/usr/bin/env python3
"""
Scheduler para tarefas de limpeza automática

Este script pode ser executado via cron para agendar limpezas regulares:
- Limpeza de arquivos S3 temporários (diário)
- Remoção de uploads órfãos (diário)
- Limpeza de uploads expirados (a cada 6 horas)

Exemplo de crontab:
# Limpeza diária às 2:00 AM
0 2 * * * /path/to/venv/bin/python /path/to/cleanup_scheduler.py --daily

# Limpeza de uploads expirados a cada 6 horas
0 */6 * * * /path/to/venv/bin/python /path/to/cleanup_scheduler.py --expired-uploads
"""

import argparse
import logging
import sys
from datetime import datetime

# Adicionar projeto ao path
sys.path.append('.')

from infrastructure.queue.redis_queue import redis_queue_service

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def schedule_s3_cleanup(older_than_hours: int = 24) -> str:
    """
    Agenda limpeza de arquivos S3 temporários
    
    Args:
        older_than_hours: Remover arquivos mais antigos que X horas
        
    Returns:
        str: ID do job criado
    """
    try:
        job_id = redis_queue_service.enqueue_cleanup_task(
            task_type='s3_cleanup',
            older_than_hours=older_than_hours
        )
        
        logger.info(f"Limpeza S3 agendada - Job: {job_id}, older_than: {older_than_hours}h")
        return job_id
        
    except Exception as e:
        logger.error(f"Erro ao agendar limpeza S3: {e}")
        raise


def schedule_orphaned_cleanup() -> str:
    """
    Agenda limpeza de uploads órfãos
    
    Returns:
        str: ID do job criado
    """
    try:
        job_id = redis_queue_service.enqueue_cleanup_task(
            task_type='orphaned_files'
        )
        
        logger.info(f"Limpeza de órfãos agendada - Job: {job_id}")
        return job_id
        
    except Exception as e:
        logger.error(f"Erro ao agendar limpeza de órfãos: {e}")
        raise


def schedule_expired_cleanup() -> str:
    """
    Agenda limpeza de uploads expirados
    
    Returns:
        str: ID do job criado
    """
    try:
        job_id = redis_queue_service.enqueue_cleanup_task(
            task_type='expired_uploads'
        )
        
        logger.info(f"Limpeza de expirados agendada - Job: {job_id}")
        return job_id
        
    except Exception as e:
        logger.error(f"Erro ao agendar limpeza de expirados: {e}")
        raise


def main():
    """Função principal do scheduler"""
    parser = argparse.ArgumentParser(description='Scheduler de tarefas de limpeza')
    parser.add_argument(
        '--daily', 
        action='store_true', 
        help='Executar limpeza diária completa (S3 + órfãos)'
    )
    parser.add_argument(
        '--s3-cleanup', 
        action='store_true', 
        help='Apenas limpeza S3'
    )
    parser.add_argument(
        '--orphaned-files', 
        action='store_true', 
        help='Apenas limpeza de órfãos'
    )
    parser.add_argument(
        '--expired-uploads', 
        action='store_true', 
        help='Apenas limpeza de expirados'
    )
    parser.add_argument(
        '--older-than', 
        type=int, 
        default=24, 
        help='Para S3: remover arquivos mais antigos que X horas (padrão: 24)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Simular execução sem agendar jobs'
    )
    
    args = parser.parse_args()
    
    if not any([args.daily, args.s3_cleanup, args.orphaned_files, args.expired_uploads]):
        parser.print_help()
        sys.exit(1)
    
    logger.info(f"Iniciando scheduler de limpeza - {datetime.utcnow().isoformat()}")
    
    if args.dry_run:
        logger.info("MODO DRY-RUN: Simulando execução...")
    
    jobs_created = []
    
    try:
        if args.daily:
            logger.info("Executando limpeza diária completa...")
            
            if not args.dry_run:
                # S3 cleanup
                job_id = schedule_s3_cleanup(args.older_than)
                jobs_created.append(('s3_cleanup', job_id))
                
                # Orphaned files cleanup
                job_id = schedule_orphaned_cleanup()
                jobs_created.append(('orphaned_files', job_id))
            else:
                logger.info("DRY-RUN: Agendaria limpeza S3 e órfãos")
        
        if args.s3_cleanup:
            logger.info(f"Agendando limpeza S3 (older_than: {args.older_than}h)...")
            
            if not args.dry_run:
                job_id = schedule_s3_cleanup(args.older_than)
                jobs_created.append(('s3_cleanup', job_id))
            else:
                logger.info("DRY-RUN: Agendaria limpeza S3")
        
        if args.orphaned_files:
            logger.info("Agendando limpeza de órfãos...")
            
            if not args.dry_run:
                job_id = schedule_orphaned_cleanup()
                jobs_created.append(('orphaned_files', job_id))
            else:
                logger.info("DRY-RUN: Agendaria limpeza de órfãos")
        
        if args.expired_uploads:
            logger.info("Agendando limpeza de expirados...")
            
            if not args.dry_run:
                job_id = schedule_expired_cleanup()
                jobs_created.append(('expired_uploads', job_id))
            else:
                logger.info("DRY-RUN: Agendaria limpeza de expirados")
        
        # Resumo
        if jobs_created:
            logger.info(f"Jobs criados com sucesso: {len(jobs_created)}")
            for task_type, job_id in jobs_created:
                logger.info(f"  - {task_type}: {job_id}")
        elif args.dry_run:
            logger.info("DRY-RUN concluído com sucesso")
        else:
            logger.warning("Nenhum job foi criado")
        
    except Exception as e:
        logger.error(f"Erro no scheduler: {e}")
        sys.exit(1)
    
    logger.info("Scheduler finalizado com sucesso")


if __name__ == '__main__':
    main()
