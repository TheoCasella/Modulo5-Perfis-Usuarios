# Composition Root — unico lugar que conhece adapters concretos.

from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.adapters.driven.persistence.repositorio_auditoria_sqlite import (
    RepositorioAuditoriaSQLite,
)
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.application.services.saude_service_impl import SaudeServiceImpl
from app.config import settings


class CompositionRoot:

    def __init__(self):
        backend = (settings.AUDITORIA_BACKEND or "sqlite").lower()
        if backend == "memoria":
            self.repositorio_auditoria = RepositorioAuditoriaMemoria()
        elif backend == "sqlite":
            self.repositorio_auditoria = RepositorioAuditoriaSQLite(settings.AUDITORIA_SQLITE_PATH)
        else:
            raise ValueError(f"AUDITORIA_BACKEND desconhecido: {backend}")

        self.auditoria_service = AuditoriaServiceImpl(self.repositorio_auditoria)
        self.saude_service = SaudeServiceImpl(self.repositorio_auditoria)

    def get_auditoria_service(self) -> AuditoriaServiceImpl:
        return self.auditoria_service

    def get_saude_service(self) -> SaudeServiceImpl:
        return self.saude_service


_singleton: CompositionRoot | None = None


def get_root() -> CompositionRoot:
    """Reusa a mesma instancia entre requests para preservar conexao SQLite + memoria."""
    global _singleton
    if _singleton is None:
        _singleton = CompositionRoot()
    return _singleton
