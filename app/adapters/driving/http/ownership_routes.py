# Rotas HTTP para consulta resiliente e gerenciamento de ownership (US PU-09 + PU-02).

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.ports.driving.ownership_service import OwnershipService
from app.config.composition_root import get_root
from app.domain.excecoes import OwnershipNaoEncontradoError


router = APIRouter(prefix="/api/ownership", tags=["Ownership"])


def get_ownership_service() -> OwnershipService:
    return get_root().get_ownership_service()


class RegistrarModulosRequest(BaseModel):
    repositorio: str
    modulos: List[str]


@router.get("")
def obter_owner(
    repositorio: str = Query(..., description="No formato owner/repo"),
    modulo: str = Query(..., description="Caminho do arquivo/diretorio"),
    service: OwnershipService = Depends(get_ownership_service),
):
    try:
        resposta = service.obter_owner(repositorio, modulo)
    except OwnershipNaoEncontradoError as e:
        raise HTTPException(status_code=503, detail={"mensagem": str(e)})
    return resposta.to_dict()


@router.get("/conhecidos")
def listar_conhecidos(
    repositorio: Optional[str] = Query(default=None),
    service: OwnershipService = Depends(get_ownership_service),
):
    """Lista ownerships ja em cache — nao chama o GitHub. Util quando ele esta fora."""
    items = service.listar_owners_conhecidos(repositorio)
    return {"ownerships": [o.to_dict() for o in items]}


@router.post("/registrar", status_code=201)
def registrar_modulos(
    payload: RegistrarModulosRequest,
    service: OwnershipService = Depends(get_ownership_service),
):
    """
    Registra modulos para serem rastreados pelo job diario (US PU-02).
    Tenta consultar o GitHub agora; se falhar, cria entrada placeholder.
    """
    if not payload.repositorio or not payload.modulos:
        raise HTTPException(status_code=400, detail="repositorio e modulos sao obrigatorios.")
    registrados = []
    for modulo in payload.modulos:
        if not modulo or not modulo.strip():
            continue
        ownership = service.registrar_modulo(payload.repositorio, modulo.strip())
        registrados.append(ownership.to_dict())
    return {"registrados": registrados, "total": len(registrados)}


@router.post("/refrescar")
def refrescar(service: OwnershipService = Depends(get_ownership_service)):
    """
    Dispara manualmente o refresh de todos os ownerships conhecidos.
    Mesmo trabalho que o job diario faz — util para forcar atualizacao sob demanda.
    """
    resultado = service.refrescar_todos()
    return resultado.to_dict()
