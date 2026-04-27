# Implementação do SaudeService
# Responsabilidade: health check do serviço (liveness e readiness).

from datetime import datetime, timezone
from typing import Dict

from app.application.ports.driving.saude_service import SaudeService
from app.application.ports.driven.repositorio_papeis import RepositorioPapeis

VERSAO = "1.0.0"


class SaudeServiceImpl(SaudeService):

    def __init__(self, repositorio: RepositorioPapeis):
        self._repositorio = repositorio

    def verificar_liveness(self) -> Dict:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versao": VERSAO
        }

    def verificar_readiness(self) -> Dict:
        try:
            self._repositorio.listar_por_projeto("__healthcheck__")
            banco_ok = True
        except Exception:
            banco_ok = False

        if not banco_ok:
            raise RuntimeError("Banco de dados indisponivel.")

        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versao": VERSAO,
            "dependencias": {"banco": "ok"}
        }