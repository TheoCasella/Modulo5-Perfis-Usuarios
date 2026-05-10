# Implementacao do OwnershipService com padrao de resiliencia (US PU-09).
# Pipeline:
#   1. Cache recente (idade <= TTL) -> devolve direto, marcado como "cache_recente"
#   2. Tenta GitHub
#      - sucesso -> persiste e devolve "github_vivo"
#      - falha   -> log + tenta cache antigo -> devolve "fallback_cache" com aviso amigavel
#   3. Sem cache + GitHub fora -> OwnershipNaoEncontradoError com mensagem amigavel

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.application.ports.driven.provedor_historico_commits import ProvedorHistoricoCommits
from app.application.ports.driven.repositorio_ownership import RepositorioOwnership
from app.application.ports.driving.ownership_service import OwnershipService, RespostaOwnership
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
        # Comparacao estrita: TTL=0 significa "sempre consultar fonte fresca",
        # nao "qualquer cache vale".
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
            # Provedor reconheceu que o caminho nao tem commits — propaga sem fallback.
            raise

    def listar_owners_conhecidos(self, repositorio: Optional[str] = None) -> List[Ownership]:
        return self._repositorio.listar(repositorio)

    def _aviso_amigavel(self, cache: Ownership, motivo: str) -> str:
        idade_min = cache.idade_segundos() // 60
        return (
            f"GitHub esta indisponivel no momento ({motivo}). "
            f"Mostrando o owner conhecido ha {idade_min} min — pode estar desatualizado."
        )
