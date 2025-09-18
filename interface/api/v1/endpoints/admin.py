from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from domain.entities.prefeitura import Prefeitura
from domain.entities.usuario import Usuario
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.prefeitura_repository import PrefeituraRepository
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.value_objects.usuario_id import UsuarioId
from interface.dependencies.container import (
    get_postgres_prefeitura_repository,
    get_postgres_usuario_repository,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# Endpoints para Prefeituras
@router.post("/prefeituras", response_model=dict)
async def create_prefeitura(
    nome: str,
    quota_tokens: int = 10000,
    prefeitura_repo: PrefeituraRepository = Depends(get_postgres_prefeitura_repository),
):
    """Cria uma nova prefeitura"""
    try:
        prefeitura = Prefeitura.create(nome=nome, quota_tokens=quota_tokens)
        await prefeitura_repo.save(prefeitura)

        return {
            "id": str(prefeitura.id),
            "nome": prefeitura.nome,
            "quota_tokens": prefeitura.quota_tokens,
            "tokens_consumidos": prefeitura.tokens_consumidos,
            "ativo": prefeitura.ativo,
            "criado_em": prefeitura.criado_em.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/prefeituras", response_model=List[dict])
async def list_prefeituras(
    limit: Optional[int] = 50,
    offset: int = 0,
    prefeitura_repo: PrefeituraRepository = Depends(get_postgres_prefeitura_repository),
):
    """Lista prefeituras ativas"""
    try:
        prefeituras = await prefeitura_repo.find_all_active(limit=limit, offset=offset)

        return [
            {
                "id": str(p.id),
                "nome": p.nome,
                "quota_tokens": p.quota_tokens,
                "tokens_consumidos": p.tokens_consumidos,
                "tokens_restantes": p.tokens_restantes,
                "percentual_consumo": p.percentual_consumo,
                "ativo": p.ativo,
                "criado_em": p.criado_em.isoformat(),
            }
            for p in prefeituras
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar prefeituras: {e}")


@router.get("/prefeituras/{prefeitura_id}", response_model=dict)
async def get_prefeitura(
    prefeitura_id: UUID,
    prefeitura_repo: PrefeituraRepository = Depends(get_postgres_prefeitura_repository),
):
    """Busca prefeitura por ID"""
    try:
        prefeitura = await prefeitura_repo.find_by_id(
            PrefeituraId.from_uuid(prefeitura_id)
        )

        if not prefeitura:
            raise HTTPException(status_code=404, detail="Prefeitura não encontrada")

        return {
            "id": str(prefeitura.id),
            "nome": prefeitura.nome,
            "quota_tokens": prefeitura.quota_tokens,
            "tokens_consumidos": prefeitura.tokens_consumidos,
            "tokens_restantes": prefeitura.tokens_restantes,
            "percentual_consumo": prefeitura.percentual_consumo,
            "quota_esgotada": prefeitura.quota_esgotada,
            "quota_critica": prefeitura.quota_critica,
            "ativo": prefeitura.ativo,
            "criado_em": prefeitura.criado_em.isoformat(),
            "atualizado_em": prefeitura.atualizado_em.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Endpoints para Usuários
@router.post("/usuarios", response_model=dict)
async def create_usuario(
    nome: str,
    email: str,
    prefeitura_id: Optional[UUID] = None,
    usuario_repo: UsuarioRepository = Depends(get_postgres_usuario_repository),
):
    """Cria um novo usuário"""
    try:
        prefeitura_id_obj = (
            PrefeituraId.from_uuid(prefeitura_id) if prefeitura_id else None
        )
        usuario = Usuario.create(
            nome=nome, email=email, prefeitura_id=prefeitura_id_obj
        )
        await usuario_repo.save(usuario)

        return {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
            "prefeitura_id": (
                str(usuario.prefeitura_id) if usuario.prefeitura_id else None
            ),
            "is_anonimo": usuario.is_anonimo,
            "ativo": usuario.ativo,
            "criado_em": usuario.criado_em.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usuarios", response_model=List[dict])
async def list_usuarios(
    prefeitura_id: Optional[UUID] = None,
    limit: Optional[int] = 50,
    offset: int = 0,
    usuario_repo: UsuarioRepository = Depends(get_postgres_usuario_repository),
):
    """Lista usuários"""
    try:
        if prefeitura_id:
            usuarios = await usuario_repo.find_by_prefeitura_id(
                PrefeituraId.from_uuid(prefeitura_id), limit=limit, offset=offset
            )
        else:
            usuarios = await usuario_repo.find_all_active(limit=limit, offset=offset)

        return [
            {
                "id": str(u.id),
                "nome": u.nome,
                "email": u.email,
                "prefeitura_id": str(u.prefeitura_id) if u.prefeitura_id else None,
                "is_anonimo": u.is_anonimo,
                "ativo": u.ativo,
                "criado_em": u.criado_em.isoformat(),
            }
            for u in usuarios
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar usuários: {e}")


@router.get("/usuarios/{usuario_id}", response_model=dict)
async def get_usuario(
    usuario_id: UUID,
    usuario_repo: UsuarioRepository = Depends(get_postgres_usuario_repository),
):
    """Busca usuário por ID"""
    try:
        usuario = await usuario_repo.find_by_id(UsuarioId.from_uuid(usuario_id))

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        return {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
            "prefeitura_id": (
                str(usuario.prefeitura_id) if usuario.prefeitura_id else None
            ),
            "is_anonimo": usuario.is_anonimo,
            "tem_prefeitura": usuario.tem_prefeitura,
            "tem_autenticacao": usuario.tem_autenticacao,
            "email_domain": usuario.email_domain,
            "ativo": usuario.ativo,
            "criado_em": usuario.criado_em.isoformat(),
            "atualizado_em": usuario.atualizado_em.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Endpoints de estatísticas
@router.get("/stats", response_model=dict)
async def get_admin_stats(
    prefeitura_repo: PrefeituraRepository = Depends(get_postgres_prefeitura_repository),
    usuario_repo: UsuarioRepository = Depends(get_postgres_usuario_repository),
):
    """Estatísticas administrativas"""
    try:
        total_prefeituras = await prefeitura_repo.count()
        prefeituras_ativas = await prefeitura_repo.count_active()
        total_usuarios = await usuario_repo.count()
        usuarios_ativos = await usuario_repo.count_active()
        usuarios_anonimos = await usuario_repo.count_anonimos()

        prefeituras_quota_critica = await prefeitura_repo.find_by_quota_critica()
        prefeituras_quota_esgotada = await prefeitura_repo.find_by_quota_esgotada()

        return {
            "prefeituras": {
                "total": total_prefeituras,
                "ativas": prefeituras_ativas,
                "quota_critica": len(prefeituras_quota_critica),
                "quota_esgotada": len(prefeituras_quota_esgotada),
            },
            "usuarios": {
                "total": total_usuarios,
                "ativos": usuarios_ativos,
                "anonimos": usuarios_anonimos,
                "vinculados": total_usuarios - usuarios_anonimos,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {e}")
