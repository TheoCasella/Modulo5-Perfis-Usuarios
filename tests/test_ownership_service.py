# Testes do OwnershipServiceImpl — cobre a logica de resiliencia (US PU-09).

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from app.adapters.driven.clients.provedor_historico_commits_fake import (
    ProvedorHistoricoCommitsFake,
)
from app.application.ports.driven.repositorio_ownership import RepositorioOwnership
from app.application.services.ownership_service_impl import OwnershipServiceImpl
from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError, OwnershipNaoEncontradoError


class _RepoMemoria(RepositorioOwnership):
    def __init__(self):
        self._dados: dict = {}

    def salvar(self, o: Ownership) -> None:
        self._dados[(o.repositorio, o.modulo)] = o

    def obter(self, repositorio: str, modulo: str) -> Optional[Ownership]:
        return self._dados.get((repositorio, modulo))

    def listar(self, repositorio: Optional[str] = None) -> list:
        if repositorio is None:
            return list(self._dados.values())
        return [o for o in self._dados.values() if o.repositorio == repositorio]


def _ownership(repo="r", modulo="m", owner="alice", idade_segundos=0):
    return Ownership(
        repositorio=repo,
        modulo=modulo,
        owner_id=owner,
        confianca=0.8,
        total_commits=10,
        ultima_atualizacao=datetime.now(timezone.utc) - timedelta(seconds=idade_segundos),
    )


def test_cache_recente_devolve_sem_chamar_github():
    fake = ProvedorHistoricoCommitsFake()
    fake.fazer_falhar_com(GitHubIndisponivelError("nao deveria ser chamado"))
    repo = _RepoMemoria()
    repo.salvar(_ownership(idade_segundos=10))

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    resp = service.obter_owner("r", "m")

    assert resp.origem == "cache_recente"
    assert resp.aviso is None
    assert resp.ownership.owner_id == "alice"


def test_cache_velho_consulta_github_e_atualiza():
    fake = ProvedorHistoricoCommitsFake()
    fake.configurar("r", "m", _ownership(owner="bob"))
    repo = _RepoMemoria()
    repo.salvar(_ownership(owner="alice", idade_segundos=10_000))

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    resp = service.obter_owner("r", "m")

    assert resp.origem == "github_vivo"
    assert resp.ownership.owner_id == "bob"
    assert repo.obter("r", "m").owner_id == "bob"  # cache atualizado


def test_github_indisponivel_com_cache_devolve_fallback():
    fake = ProvedorHistoricoCommitsFake()
    fake.fazer_falhar_com(GitHubIndisponivelError("502"))
    repo = _RepoMemoria()
    repo.salvar(_ownership(owner="alice", idade_segundos=10_000))

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    resp = service.obter_owner("r", "m")

    assert resp.origem == "fallback_cache"
    assert resp.ownership.owner_id == "alice"
    assert resp.aviso is not None
    assert "indisponivel" in resp.aviso.lower()
    assert "min" in resp.aviso  # menciona idade do cache


def test_github_indisponivel_sem_cache_levanta_erro_amigavel():
    fake = ProvedorHistoricoCommitsFake()
    fake.fazer_falhar_com(GitHubIndisponivelError("rate limit"))
    repo = _RepoMemoria()

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    with pytest.raises(OwnershipNaoEncontradoError) as exc_info:
        service.obter_owner("r", "m")

    msg = str(exc_info.value).lower()
    assert "tente novamente" in msg or "tente mais tarde" in msg
    assert "github" in msg or "rate" in msg


def test_falha_eh_logada(caplog):
    fake = ProvedorHistoricoCommitsFake()
    fake.fazer_falhar_com(GitHubIndisponivelError("503"))
    repo = _RepoMemoria()
    repo.salvar(_ownership(idade_segundos=10_000))

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    with caplog.at_level(logging.WARNING, logger="perfis.ownership"):
        service.obter_owner("r", "m")

    assert any("indisponivel" in rec.message.lower() for rec in caplog.records)


def test_modulo_inexistente_sem_cache_propaga_nao_encontrado():
    """Se GitHub diz 'nao tem commits', isso e diferente de 'nao consigo falar com github'."""
    fake = ProvedorHistoricoCommitsFake()  # vazio, levanta OwnershipNaoEncontradoError
    repo = _RepoMemoria()

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    with pytest.raises(OwnershipNaoEncontradoError):
        service.obter_owner("r", "m")


def test_listar_owners_so_le_cache():
    fake = ProvedorHistoricoCommitsFake()
    fake.fazer_falhar_com(GitHubIndisponivelError("nao deveria ser chamado"))
    repo = _RepoMemoria()
    repo.salvar(_ownership(repo="r1", owner="alice"))
    repo.salvar(_ownership(repo="r2", owner="bob"))

    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    todos = service.listar_owners_conhecidos()
    assert len(todos) == 2

    so_r1 = service.listar_owners_conhecidos(repositorio="r1")
    assert len(so_r1) == 1
    assert so_r1[0].owner_id == "alice"
