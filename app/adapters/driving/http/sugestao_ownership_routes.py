# Rotas REST para sugestao e atribuicao de owner de documentos orfaos (US PU-03).

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.ports.driving.sugestao_ownership_service import (
    SugestaoOwnershipService,
)
from app.config.composition_root import get_root
from app.domain.excecoes import (
    DocumentoNaoEncontradoError,
    OwnershipJaAtribuidoError,
    SemCandidatoOwnerError,
    SugestaoOwnershipInvalidaError,
)


router = APIRouter(prefix="/api/sugestao-ownership", tags=["SugestaoOwnership"])


def get_service() -> SugestaoOwnershipService:
    return get_root().get_sugestao_ownership_service()


class AprovarRequest(BaseModel):
    aprovador_id: str
    owner_id: str
    motivo: str = ""


class ReatribuirRequest(BaseModel):
    aprovador_id: str
    novo_owner_id: str
    motivo: str


@router.get("/orfaos")
def listar_orfaos(
    projeto_id: Optional[str] = Query(default=None),
    service: SugestaoOwnershipService = Depends(get_service),
):
    """Documentos PU-05 que ainda nao tem owner atribuido."""
    docs = service.listar_orfaos(projeto_id=projeto_id)
    return {"orfaos": [d.to_dict() for d in docs], "total": len(docs)}


@router.get("/atribuidos")
def listar_atribuidos(service: SugestaoOwnershipService = Depends(get_service)):
    return {"atribuidos": [o.to_dict() for o in service.listar_atribuidos()]}


@router.get("/{documento_id}/owner")
def obter_owner_documento(
    documento_id: str, service: SugestaoOwnershipService = Depends(get_service),
):
    owner = service.obter_owner(documento_id)
    if owner is None:
        raise HTTPException(status_code=404, detail=f"Documento {documento_id} esta orfao (sem owner).")
    return owner.to_dict()


@router.get("/{documento_id}/sugerir")
def sugerir(
    documento_id: str, service: SugestaoOwnershipService = Depends(get_service),
):
    """Calcula candidato a owner com base no historico de auditoria. Nao persiste."""
    try:
        sugestao = service.sugerir(documento_id)
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SemCandidatoOwnerError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return sugestao.to_dict()


@router.post("/{documento_id}/aprovar", status_code=201)
def aprovar(
    documento_id: str,
    payload: AprovarRequest,
    service: SugestaoOwnershipService = Depends(get_service),
):
    """Aprovador decide quem sera o owner — pode ou nao ser o sugerido."""
    try:
        ownership = service.aprovar_sugestao(
            documento_id=documento_id,
            aprovador_id=payload.aprovador_id,
            owner_id=payload.owner_id,
            motivo=payload.motivo,
        )
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OwnershipJaAtribuidoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SugestaoOwnershipInvalidaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ownership.to_dict()


@router.post("/{documento_id}/reatribuir")
def reatribuir(
    documento_id: str,
    payload: ReatribuirRequest,
    service: SugestaoOwnershipService = Depends(get_service),
):
    """Substitui owner existente. Motivo eh obrigatorio (auditoria)."""
    try:
        ownership = service.reatribuir(
            documento_id=documento_id,
            aprovador_id=payload.aprovador_id,
            novo_owner_id=payload.novo_owner_id,
            motivo=payload.motivo,
        )
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SugestaoOwnershipInvalidaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ownership.to_dict()
