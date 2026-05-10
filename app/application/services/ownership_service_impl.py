# Implementacao do OwnershipService.
# US PU-09: padrao de resiliencia (cache -> github -> fallback).
# US PU-02: refresh em lote + registrar_modulo para o job diario.

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.application.ports.driven.provedor_historico_commits import ProvedorHistoricoCommits
from app.application.ports.driven.repositorio_ownership import RepositorioOwnership
from app.application.ports.driving.ownership_service import (
    OwnershipService, RespostaOwnership, ResultadoRefresh,
)
from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError, OwnershipNaoEncontradoError


_logger = logging.getLogger("perfis.ownership")


class OwnershipServiceImpl(OwnershipService):

    def __init__(
        self,
        provedor_historico: ProvedorHistoricoCommits,
        repositorio: RepositorioOwnership,
        cache_ttl_segundos: int = 3600,
    ):
        self._provedor = provedor_historico
        self._repositorio = repositorio
        self._ttl = cache_ttl_segundos

    def obter_owner(self, repositorio: str, modulo: str) -> RespostaOwnership:
        cache = self._repositorio.obter(repositorio, modulo)
        if cache is not None and cache.idade_segundos() < self._ttl:
            return RespostaOwnership(ownership=cache, origem="cache_recente")

        try:
            fresco = self._provedor.identificar_owner(repositorio, modulo)
            self._repositorio.salvar(fresco)
            return RespostaOwnership(ownership=fresco, origem="github_vivo")
        except GitHubIndisponivelError as e:
            _logger.warning(
                "GitHub indisponivel ao consultar ownership de %s/%s: %s",
                repositorio, modulo, e,
                extra={"repositorio": repositorio, "modulo": modulo, "erro": str(e)},
            )
            if cache is not None:
                aviso = self._aviso_amigavel(cache, motivo=str(e))
                return RespostaOwnership(ownership=cache, origem="fallback_cache", aviso=aviso)
            raise OwnershipNaoEncontradoError(
                f"Nao temos owner conhecido para '{modulo}' em '{repositorio}' "
                f"e a consulta ao GitHub falhou agora ({e}). "
                f"Por favor tente novamente em alguns minutos."
            ) from e
        except OwnershipNaoEncontradoError:
            raise

    def listar_owners_conhecidos(self, repositorio: Optional[str] = None) -> List[Ownership]:
        return self._repositorio.listar(repositorio)

    def registrar_modulo(self, repositorio: str, modulo: str) -> Ownership:
        existente = self._repositorio.obter(repositorio, modulo)
        if existente is not None:
            return existente
        try:
            fresco = self._provedor.identificar_owner(repositorio, modulo)
            self._repositorio.salvar(fresco)
            return fresco
        except (GitHubIndisponivelError, OwnershipNaoEncontradoError) as e:
            placeholder = Ownership(
                repositorio=repositorio, modulo=modulo,
                owner_id="(desconhecido)", confianca=0.0, total_commits=0,
            )
            self._repositorio.salvar(placeholder)
            _logger.info(
                "Modulo %s/%s registrado como placeholder (consulta inicial falhou: %s)",
                repositorio, modulo, e,
            )
            return placeholder

    def refrescar_todos(self) -> ResultadoRefresh:
        inicio = datetime.now(timezone.utc)
        conhecidos = self._repositorio.listar()

        refrescados = 0
        sem_mudanca = 0
        falhas = 0
        erros: List[str] = []

        for atual in conhecidos:
            try:
                novo = self._provedor.identificar_owner(atual.repositorio, atual.modulo)
            except OwnershipNaoEncontradoError:
                sem_mudanca += 1
                continue
            except GitHubIndisponivelError as e:
                falhas += 1
                erros.append(f"{atual.repositorio}/{atual.modulo}: {e}")
                continue

            if (
                novo.owner_id == atual.owner_id
                and novo.total_commits == atual.total_commits
                and abs(novo.confianca - atual.confianca) < 1e-6
            ):
                sem_mudanca += 1
                continue

            self._repositorio.salvar(novo)
            refrescados += 1

        fim = datetime.now(timezone.utc)
        resultado = ResultadoRefresh(
            inicio=inicio, fim=fim,
            total_avaliados=len(conhecidos),
            refrescados=refrescados, sem_mudanca=sem_mudanca,
            falhas=falhas, erros=tuple(erros[:20]),  # limita pra nao explodir log
        )
        _logger.info(
            "Refresh diario concluido: %d avaliados, %d refrescados, %d sem mudanca, %d falhas",
            resultado.total_avaliados, resultado.refrescados,
            resultado.sem_mudanca, resultado.falhas,
        )
        return resultado

    def _aviso_amigavel(self, cache: Ownership, motivo: str) -> str:
        idade_min = cache.idade_segundos() // 60
        return (
            f"GitHub esta indisponivel no momento ({motivo}). "
            f"Mostrando o owner conhecido ha {idade_min} min — pode estar desatualizado."
        )
