# Adaptador driven: cliente HTTP para GitHub commits API.
# Implementacao MVP — PU-02 vai refinar (paginacao completa, ranking ponderado, etc).

import logging
from collections import Counter
from typing import Optional

import httpx

from app.application.ports.driven.provedor_historico_commits import (
    ProvedorHistoricoCommits,
)
from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError, OwnershipNaoEncontradoError


_logger = logging.getLogger("perfis.github")


class ClienteGitHubCommits(ProvedorHistoricoCommits):

    def __init__(
        self,
        base_url: str = "https://api.github.com",
        token: Optional[str] = None,
        timeout_segundos: float = 5.0,
        per_page: int = 100,
    ):
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_segundos
        self._per_page = max(1, min(per_page, 100))

    def identificar_owner(self, repositorio: str, modulo: str) -> Ownership:
        url = f"{self._base}/repos/{repositorio}/commits"
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        params = {"path": modulo, "per_page": self._per_page}

        try:
            with httpx.Client(timeout=self._timeout) as cliente:
                resposta = cliente.get(url, headers=headers, params=params)
        except httpx.HTTPError as e:
            raise GitHubIndisponivelError(f"erro de rede ao consultar GitHub: {e}") from e

        if resposta.status_code in (502, 503, 504):
            raise GitHubIndisponivelError(f"GitHub respondeu {resposta.status_code}")
        if resposta.status_code == 404:
            raise OwnershipNaoEncontradoError(
                f"Caminho '{modulo}' nao encontrado em '{repositorio}'."
            )
        if resposta.status_code == 403:
            # Tipicamente rate-limit — tratamos como indisponibilidade temporaria
            raise GitHubIndisponivelError(
                f"GitHub bloqueou a chamada (403, possivel rate-limit): {resposta.text[:200]}"
            )
        if resposta.status_code >= 400:
            raise GitHubIndisponivelError(
                f"GitHub respondeu {resposta.status_code}: {resposta.text[:200]}"
            )

        try:
            commits = resposta.json()
        except ValueError as e:
            raise GitHubIndisponivelError(f"resposta do GitHub nao eh JSON: {e}") from e

        if not commits:
            raise OwnershipNaoEncontradoError(
                f"Nao ha commits para '{modulo}' em '{repositorio}'."
            )

        contagem = Counter()
        for commit in commits:
            login = self._extrair_autor(commit)
            if login:
                contagem[login] += 1

        if not contagem:
            raise OwnershipNaoEncontradoError(
                f"Commits encontrados em '{modulo}' nao tem autor identificavel."
            )

        owner_id, total_owner = contagem.most_common(1)[0]
        total = sum(contagem.values())
        return Ownership(
            repositorio=repositorio,
            modulo=modulo,
            owner_id=owner_id,
            confianca=total_owner / total if total else 0.0,
            total_commits=total,
        )

    @staticmethod
    def _extrair_autor(commit: dict) -> Optional[str]:
        autor = commit.get("author")
        if isinstance(autor, dict) and autor.get("login"):
            return autor["login"]
        commit_data = commit.get("commit") or {}
        autor_dados = commit_data.get("author") or {}
        if autor_dados.get("email"):
            return autor_dados["email"]
        return None
