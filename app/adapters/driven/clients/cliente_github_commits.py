# Adaptador driven: cliente HTTP para GitHub commits API.
# US PU-09: estrutura basica + identificacao por contagem.
# US PU-02: paginacao completa + janela temporal opcional.

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Optional

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
        max_paginas: int = 5,
        janela_dias: int = 0,
    ):
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_segundos
        self._per_page = max(1, min(per_page, 100))
        self._max_paginas = max(1, max_paginas)
        self._janela_dias = max(0, janela_dias)

    def identificar_owner(self, repositorio: str, modulo: str) -> Ownership:
        commits = self._coletar_commits(repositorio, modulo)
        if not commits:
            raise OwnershipNaoEncontradoError(
                f"Nao ha commits para '{modulo}' em '{repositorio}'"
                + (f" nos ultimos {self._janela_dias} dias." if self._janela_dias else ".")
            )

        contagem: Counter = Counter()
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

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _coletar_commits(self, repositorio: str, modulo: str) -> List[dict]:
        """Pagina ate max_paginas, parando antes se a pagina veio incompleta."""
        url = f"{self._base}/repos/{repositorio}/commits"
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        params_base = {"path": modulo, "per_page": self._per_page}
        if self._janela_dias > 0:
            since = datetime.now(timezone.utc) - timedelta(days=self._janela_dias)
            params_base["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        commits: List[dict] = []
        with httpx.Client(timeout=self._timeout) as cliente:
            for pagina in range(1, self._max_paginas + 1):
                params = {**params_base, "page": pagina}
                try:
                    resposta = cliente.get(url, headers=headers, params=params)
                except httpx.HTTPError as e:
                    raise GitHubIndisponivelError(
                        f"erro de rede ao consultar GitHub (pagina {pagina}): {e}"
                    ) from e

                self._exigir_status_aceitavel(resposta, modulo, repositorio)
                try:
                    lote = resposta.json()
                except ValueError as e:
                    raise GitHubIndisponivelError(f"resposta do GitHub nao eh JSON: {e}") from e

                if not lote:
                    break
                commits.extend(lote)
                if len(lote) < self._per_page:
                    break  # ultima pagina
        return commits

    @staticmethod
    def _exigir_status_aceitavel(resposta: httpx.Response, modulo: str, repositorio: str) -> None:
        if resposta.status_code == 200:
            return
        if resposta.status_code == 404:
            raise OwnershipNaoEncontradoError(
                f"Caminho '{modulo}' nao encontrado em '{repositorio}'."
            )
        if resposta.status_code in (502, 503, 504):
            raise GitHubIndisponivelError(f"GitHub respondeu {resposta.status_code}")
        if resposta.status_code in (403, 429):
            raise GitHubIndisponivelError(
                f"GitHub bloqueou ({resposta.status_code}, possivel rate-limit): "
                f"{resposta.text[:200]}"
            )
        raise GitHubIndisponivelError(
            f"GitHub respondeu {resposta.status_code}: {resposta.text[:200]}"
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
