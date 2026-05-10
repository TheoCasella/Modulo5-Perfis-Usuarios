# Adaptador driving: REST de auditoria (US PU-06).
# Append-only: ha POST para registrar e GET para consultar — sem PUT/DELETE.

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.application.ports.driving.auditoria_service import AuditoriaService
from app.config.composition_root import get_root
from app.domain.entidades.registro_auditoria import FiltroAuditoria, TipoAcao
from app.domain.excecoes import AuditoriaInvalidaError, FiltroAuditoriaInvalidoError


router = APIRouter(prefix="/api/auditoria", tags=["Auditoria"])


def get_auditoria_service() -> AuditoriaService:
    return get_root().get_auditoria_service()


class RegistrarAcaoRequest(BaseModel):
    usuario_id: str
    tipo_acao: str = Field(..., description="Um valor de TipoAcao (visualizou, editou, ...)")
    tipo_recurso: str
    recurso_id: str
    detalhes: Dict[str, Any] = Field(default_factory=dict)


def _parse_tipo_acao(valor: str) -> TipoAcao:
    try:
        return TipoAcao(valor)
    except ValueError:
        validos = ", ".join(t.value for t in TipoAcao)
        raise HTTPException(
            status_code=400,
            detail=f"tipo_acao invalido: '{valor}'. Validos: {validos}.",
        )


@router.post("/registrar", status_code=201)
def registrar(
    payload: RegistrarAcaoRequest,
    service: AuditoriaService = Depends(get_auditoria_service),
):
    tipo = _parse_tipo_acao(payload.tipo_acao)
    try:
        registro = service.registrar_acao(
            usuario_id=payload.usuario_id,
            tipo_acao=tipo,
            tipo_recurso=payload.tipo_recurso,
            recurso_id=payload.recurso_id,
            detalhes=payload.detalhes,
        )
    except AuditoriaInvalidaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return registro.to_dict()


@router.get("")
def consultar(
    service: AuditoriaService = Depends(get_auditoria_service),
    usuario_id: Optional[str] = Query(default=None),
    tipo_acao: Optional[str] = Query(default=None),
    tipo_recurso: Optional[str] = Query(default=None),
    recurso_id: Optional[str] = Query(default=None),
    desde: Optional[datetime] = Query(default=None, description="ISO 8601, inclusive"),
    ate: Optional[datetime] = Query(default=None, description="ISO 8601, inclusive"),
    limite: int = Query(default=100, ge=1, le=1000),
) -> Dict[str, List[Dict[str, Any]]]:
    tipo_acao_enum = _parse_tipo_acao(tipo_acao) if tipo_acao else None
    filtros = FiltroAuditoria(
        usuario_id=usuario_id,
        tipo_acao=tipo_acao_enum,
        tipo_recurso=tipo_recurso,
        recurso_id=recurso_id,
        desde=desde,
        ate=ate,
        limite=limite,
    )
    try:
        registros = service.consultar(filtros)
    except FiltroAuditoriaInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"registros": [r.to_dict() for r in registros]}
