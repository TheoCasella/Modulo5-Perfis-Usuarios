# Adaptador driving: rotas HTTP de health check.
# Endpoints exigidos pelo Interface-e-Nuvem em PERFIS_URL.

from fastapi import APIRouter, Depends, Response

from app.application.ports.driving.saude_service import SaudeService
from app.config.composition_root import get_root


router = APIRouter(prefix="/health", tags=["Saude"])


def get_saude_service() -> SaudeService:
    return get_root().get_saude_service()


@router.get("")
def liveness(service: SaudeService = Depends(get_saude_service)):
    return service.verificar_liveness()


@router.get("/ready")
def readiness(response: Response, service: SaudeService = Depends(get_saude_service)):
    resultado = service.verificar_readiness()
    if resultado.get("status") != "ready":
        response.status_code = 503
    return resultado
