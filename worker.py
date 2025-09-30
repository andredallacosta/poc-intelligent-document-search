"""
Redis Queue Worker para processamento de documentos

Este script inicia workers que processam jobs de forma assíncrona:
- Processamento de documentos (extração, chunking, embeddings)
- Tarefas de limpeza (S3, arquivos órfãos)

Usage:
    python worker.py                    # Worker padrão (document_processing)
    python worker.py --queues cleanup   # Worker apenas para limpeza
    python worker.py --all              # Worker para todas as filas
    python worker.py --verbose          # Logs detalhados
"""

import argparse
import logging
import sys
from typing import List

from rq import Worker
from redis import Redis

from infrastructure.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_redis_connection() -> Redis:
    """Cria conexão Redis para workers"""
    return Redis.from_url(
        settings.get_redis_url(),
        decode_responses=False
    )

def get_queue_names(args) -> List[str]:
    """Determina quais filas o worker deve processar"""
    if args.all:
        return ['document_processing', 'cleanup_tasks']
    elif args.queues:
        return args.queues.split(',')
    else:
        return ['document_processing']

def main():
    """Função principal do worker"""
    parser = argparse.ArgumentParser(description='Redis Queue Worker')
    parser.add_argument(
        '--queues', 
        type=str, 
        help='Filas para processar (separadas por vírgula). Ex: document_processing,cleanup_tasks'
    )
    parser.add_argument(
        '--all', 
        action='store_true', 
        help='Processar todas as filas disponíveis'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true', 
        help='Logs detalhados (DEBUG level)'
    )
    parser.add_argument(
        '--burst', 
        action='store_true', 
        help='Modo burst: processar jobs existentes e sair'
    )
    parser.add_argument(
        '--name', 
        type=str, 
        help='Nome do worker (para identificação)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('rq.worker').setLevel(logging.DEBUG)
    
    queue_names = get_queue_names(args)
    
    try:
        redis_conn = create_redis_connection()
        redis_conn.ping()
        logger.info(f"Conectado ao Redis: {settings.redis_host}:{settings.redis_port}")
    except Exception as e:
        logger.error(f"Erro ao conectar no Redis: {e}")
        sys.exit(1)
    
    import os
    import uuid
    container_id = os.environ.get('HOSTNAME', str(uuid.uuid4())[:8])
    worker_name = args.name or f"worker-{'-'.join(queue_names)}-{container_id}"
    
    logger.info(f"Iniciando worker: {worker_name}")
    logger.info(f"Filas: {', '.join(queue_names)}")
    logger.info(f"Modo burst: {'Sim' if args.burst else 'Não'}")
    
    try:
        worker = Worker(
            queue_names,
            connection=redis_conn,
            name=worker_name
        )
        
        worker.log = logger
        
        if args.burst:
            logger.info("Executando em modo burst...")
            worker.work(burst=True)
            logger.info("Modo burst concluído. Worker finalizando.")
        else:
            logger.info("Worker iniciado. Pressione Ctrl+C para parar.")
            worker.work()
            
    except KeyboardInterrupt:
        logger.info("Worker interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no worker: {e}")
        sys.exit(1)
    finally:
        logger.info("Worker finalizado")

if __name__ == '__main__':
    main()
