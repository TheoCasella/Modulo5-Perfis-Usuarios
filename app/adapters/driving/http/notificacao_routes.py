# Rotas REST para notificacoes in-app (US PU-07).

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.ports.driving.notificacao_service import NotificacaoService
from app.config.composition_root import get_root
from app.domain.excecoes import (
    NotificacaoInvalidaError,
    NotificacaoNaoEncontradaError,
    SubscricaoDuplicadaError,
)


router = APIRouter(prefix="/api/notificacoes", tags=["Notificacoes"])


def get_notificacao_service() -> NotificacaoService:
    return get_root().get_notificacao_service()


class SeguirRequest(BaseModel):
    usuario_id: str
    documento_id: str


class MarcarLidaRequest(BaseModel):
    usuario_id: str


@router.post("/seguir", status_code=201)
def seguir(payload: SeguirRequest, service: NotificacaoService = Depends(get_notificacao_service)):
    try:
        sub = service.seguir(payload.usuario_id, payload.documento_id)
    except NotificacaoInvalidaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SubscricaoDuplicadaError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return sub.to_dict()


@router.delete("/seguir/{documento_id}", status_code=204)
def parar_de_seguir(
    documento_id: str,
    usuario_id: str = Query(..., description="ID do usuario que quer parar de seguir"),
    service: NotificacaoService = Depends(get_notificacao_service),
):
    ok = service.parar_de_seguir(usuario_id, documento_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Subscricao nao encontrada.")
    return None


@router.get("/seguidores/{documento_id}")
def listar_seguidores(
    documento_id: str, service: NotificacaoService = Depends(get_notificacao_service),
):
    return {"seguidores": service.listar_seguidores(documento_id)}


@router.get("/seguidos")
def listar_seguidos(
    usuario_id: str = Query(...),
    service: NotificacaoService = Depends(get_notificacao_service),
):
    return {"seguidos": [s.to_dict() for s in service.listar_seguidos(usuario_id)]}


@router.get("")
def listar(
    usuario_id: str = Query(...),
    lida: Optional[bool] = Query(default=None),
    documento_id: Optional[str] = Query(default=None),
    limite: int = Query(default=50, ge=1, le=500),
    service: NotificacaoService = Depends(get_notificacao_service),
):
    notificacoes = service.listar_notificacoes(
        usuario_id=usuario_id, lida=lida, documento_id=documento_id, limite=limite,
    )
    return {"notificacoes": [n.to_dict() for n in notificacoes]}


@router.get("/contagem-nao-lidas")
def contagem_nao_lidas(
    usuario_id: str = Query(...),
    service: NotificacaoService = Depends(get_notificacao_service),
):
    return {"nao_lidas": service.contar_nao_lidas(usuario_id)}


@router.post("/{notificacao_id}/marcar-lida")
def marcar_como_lida(
    notificacao_id: str,
    payload: MarcarLidaRequest,
    service: NotificacaoService = Depends(get_notificacao_service),
):
    try:
        n = service.marcar_como_lida(payload.usuario_id, notificacao_id)
    except NotificacaoNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return n.to_dict()


@router.post("/marcar-todas-lidas")
def marcar_todas_como_lidas(
    payload: MarcarLidaRequest,
    service: NotificacaoService = Depends(get_notificacao_service),
):
    return {"marcadas": service.marcar_todas_como_lidas(payload.usuario_id)}
