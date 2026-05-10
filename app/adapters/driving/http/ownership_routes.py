# Rotas HTTP para consulta resiliente de ownership (US PU-09).

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.ports.driving.ownership_service import OwnershipService
from app.config.composition_root import get_root
from app.domain.excecoes import OwnershipNaoEncontradoError


router = APIRouter(prefix="/api/ownership", tags=["Ownership"])


def get_ownership_service() -> OwnershipService:
    return get_root().get_ownership_service()


@router.get("")
def obter_owner(
    repositorio: str = Query(..., description="No formato owner/repo, ex: fnavai/Modulo5-Interface-e-Nuvem"),
    modulo: str = Query(..., description="Caminho do arquivo/diretorio dentro do repo"),
    service: OwnershipService = Depends(get_ownership_service),
):
    try:
        resposta = service.obter_owner(repositorio, modulo)
    except OwnershipNaoEncontradoError as e:
        # 503 deixa claro pra cliente que eh falha temporaria de dependencia externa,
        # nao "sua busca esta errada" (que seria 404).
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
