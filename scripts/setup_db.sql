-- Script para configurar PostgreSQL em produção
-- Execute como superuser (postgres)

-- 1. Cria o banco de dados
CREATE DATABASE intelligent_document_search 
    WITH 
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- 2. Conecta ao banco
\c intelligent_document_search

-- 3. Cria a extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 4. Cria usuário específico da aplicação (opcional, para segurança)
-- CREATE USER app_user WITH PASSWORD 'secure_password_here';
-- GRANT CONNECT ON DATABASE intelligent_document_search TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT CREATE ON SCHEMA public TO app_user;

-- 5. Verifica se tudo está funcionando
SELECT 
    'Database: ' || current_database() as info
UNION ALL
SELECT 
    'pgvector version: ' || extversion 
FROM pg_extension 
WHERE extname = 'vector';

\echo 'Banco PostgreSQL configurado para produção!'
\echo 'Próximos passos:'
\echo '1. Execute: alembic upgrade head'
\echo '2. Configure variáveis de ambiente'
\echo '3. Inicie a aplicação'
