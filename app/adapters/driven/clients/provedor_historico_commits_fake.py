# Adaptador driven fake — devolve dados programados ou levanta excecoes.
# Util para dev offline e para testar a resiliencia do OwnershipService.

from typing import Dict, Tuple

from app.application.ports.driven.provedor_historico_commits import (
    ProvedorHistoricoCommits,
)
from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError, OwnershipNaoEncontradoError


class ProvedorHistoricoCommitsFake(ProvedorHistoricoCommits):

    def __init__(self):
        self._respostas: Dict[Tuple[str, str], Ownership] = {}
        self._falha_global: Exception | None = None

    def configurar(self, repositorio: str, modulo: str, ownership: Ownership) -> None:
        self._respostas[(repositorio, modulo)] = ownership

    def fazer_falhar_com(self, excecao: Exception) -> None:
        self._falha_global = excecao

    def reset(self) -> None:
        self._respostas.clear()
        self._falha_global = None

    def identificar_owner(self, repositorio: str, modulo: str) -> Ownership:
        if self._falha_global is not None:
            raise self._falha_global
        chave = (repositorio, modulo)
        if chave in self._respostas:
            return self._respostas[chave]
        raise OwnershipNaoEncontradoError(
            f"Fake nao tem '{modulo}' configurado para '{repositorio}'."
        )
