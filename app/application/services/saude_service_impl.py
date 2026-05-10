# Implementacao do SaudeService — checa liveness e que o repositorio responde.

from datetime import datetime, timezone
from typing import Dict

from app.application.ports.driven.repositorio_auditoria import RepositorioAuditoria
from app.application.ports.driving.saude_service import SaudeService
from app.domain.entidades.registro_auditoria import FiltroAuditoria

VERSAO = "1.0.0"


class SaudeServiceImpl(SaudeService):

    def __init__(self, repositorio_auditoria: RepositorioAuditoria):
        self._repositorio = repositorio_auditoria

    def verificar_liveness(self) -> Dict:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versao": VERSAO,
        }

    def verificar_readiness(self) -> Dict:
        # Tenta uma consulta vazia para garantir que o backend de persistencia responde.
        banco_ok = True
        motivo_falha = ""
        try:
            self._repositorio.consultar(FiltroAuditoria(limite=1))
        except Exception as e:
            banco_ok = False
            motivo_falha = str(e)

        if banco_ok:
            return {
                "status": "ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "versao": VERSAO,
                "dependencias": {"persistencia_auditoria": "ok"},
            }
        return {
            "status": "unready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versao": VERSAO,
            "dependencias": {"persistencia_auditoria": f"erro: {motivo_falha}"},
        }
