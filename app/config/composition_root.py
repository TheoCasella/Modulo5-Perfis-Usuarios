# Composition Root — unico lugar que conhece adapters concretos.

import logging

from app.adapters.driven.clients.cliente_github_commits import ClienteGitHubCommits
from app.adapters.driven.clients.provedor_historico_commits_fake import (
    ProvedorHistoricoCommitsFake,
)
from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.adapters.driven.persistence.repositorio_auditoria_sqlite import (
    RepositorioAuditoriaSQLite,
)
from app.adapters.driven.persistence.repositorio_ownership_sqlite import (
    RepositorioOwnershipSQLite,
)
from app.adapters.driven.persistence.repositorio_templates_aprovacao_sqlite import (
    RepositorioTemplatesAprovacaoSQLite,
)
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.application.services.ownership_service_impl import OwnershipServiceImpl
from app.application.services.saude_service_impl import SaudeServiceImpl
from app.application.services.template_aprovacao_service_impl import (
    TemplateAprovacaoServiceImpl,
)
from app.config import settings


def _configurar_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class CompositionRoot:

    def __init__(self):
        _configurar_logging()

        # --- Auditoria (PU-06) ---
        backend_auditoria = (settings.AUDITORIA_BACKEND or "sqlite").lower()
        if backend_auditoria == "memoria":
            self.repositorio_auditoria = RepositorioAuditoriaMemoria()
        elif backend_auditoria == "sqlite":
            self.repositorio_auditoria = RepositorioAuditoriaSQLite(settings.AUDITORIA_SQLITE_PATH)
        else:
            raise ValueError(f"AUDITORIA_BACKEND desconhecido: {backend_auditoria}")

        # --- Ownership (PU-09) ---
        provedor_tipo = (settings.PROVEDOR_HISTORICO_COMMITS or "github").lower()
        if provedor_tipo == "github":
            self.provedor_historico = ClienteGitHubCommits(
                base_url=settings.GITHUB_BASE_URL,
                token=settings.GITHUB_TOKEN or None,
                timeout_segundos=settings.GITHUB_TIMEOUT_SEGUNDOS,
            )
        elif provedor_tipo == "fake":
            self.provedor_historico = ProvedorHistoricoCommitsFake()
        else:
            raise ValueError(f"PROVEDOR_HISTORICO_COMMITS desconhecido: {provedor_tipo}")

        self.repositorio_ownership = RepositorioOwnershipSQLite(settings.OWNERSHIP_SQLITE_PATH)

        # --- Templates de aprovacao (PU-04) ---
        self.repositorio_templates_aprovacao = RepositorioTemplatesAprovacaoSQLite(
            settings.TEMPLATES_APROVACAO_SQLITE_PATH
        )

        # --- Services ---
        self.auditoria_service = AuditoriaServiceImpl(self.repositorio_auditoria)
        self.saude_service = SaudeServiceImpl(self.repositorio_auditoria)
        self.ownership_service = OwnershipServiceImpl(
            provedor_historico=self.provedor_historico,
            repositorio=self.repositorio_ownership,
            cache_ttl_segundos=settings.OWNERSHIP_CACHE_TTL_SEGUNDOS,
        )
        self.template_aprovacao_service = TemplateAprovacaoServiceImpl(
            repositorio=self.repositorio_templates_aprovacao,
            auditoria=self.auditoria_service,
        )

    def get_auditoria_service(self) -> AuditoriaServiceImpl:
        return self.auditoria_service

    def get_saude_service(self) -> SaudeServiceImpl:
        return self.saude_service

    def get_ownership_service(self) -> OwnershipServiceImpl:
        return self.ownership_service

    def get_template_aprovacao_service(self) -> TemplateAprovacaoServiceImpl:
        return self.template_aprovacao_service


_singleton: CompositionRoot | None = None


def get_root() -> CompositionRoot:
    """Reusa a mesma instancia entre requests para preservar conexao SQLite + memoria."""
    global _singleton
    if _singleton is None:
        _singleton = CompositionRoot()
    return _singleton
