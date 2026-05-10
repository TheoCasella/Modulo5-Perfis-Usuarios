# Porta driving: OwnershipService
# Caso de uso: identificar owner de um modulo de forma resiliente (US PU-09)
# + refresh em lote para o job diario (US PU-02).

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.domain.entidades.ownership import Ownership


@dataclass(frozen=True)
class RespostaOwnership:
    """Wrapper que carrega o ownership + a procedencia da informacao + aviso."""
    ownership: Ownership
    origem: str          # "github_vivo" | "cache_recente" | "fallback_cache"
    aviso: Optional[str] = None  # mensagem amigavel quando degradado

    def to_dict(self) -> dict:
        return {
            "ownership": self.ownership.to_dict(),
            "origem": self.origem,
            "aviso": self.aviso,
        }


@dataclass(frozen=True)
class ResultadoRefresh:
    """Resumo do job diario que reprocessa todos os ownerships conhecidos."""
    inicio: datetime
    fim: datetime
    total_avaliados: int
    refrescados: int
    sem_mudanca: int
    falhas: int
    erros: tuple = field(default_factory=tuple)

    @property
    def duracao_segundos(self) -> float:
        return (self.fim - self.inicio).total_seconds()

    def to_dict(self) -> dict:
        return {
            "inicio": self.inicio.isoformat(),
            "fim": self.fim.isoformat(),
            "duracao_segundos": round(self.duracao_segundos, 2),
            "total_avaliados": self.total_avaliados,
            "refrescados": self.refrescados,
            "sem_mudanca": self.sem_mudanca,
            "falhas": self.falhas,
            "erros": list(self.erros),
        }


class OwnershipService(ABC):

    @abstractmethod
    def obter_owner(self, repositorio: str, modulo: str) -> RespostaOwnership:
        """Tenta GitHub; em falha, cai no ultimo registro conhecido (US PU-09)."""
        pass

    @abstractmethod
    def listar_owners_conhecidos(self, repositorio: Optional[str] = None) -> List[Ownership]:
        pass

    @abstractmethod
    def registrar_modulo(self, repositorio: str, modulo: str) -> Ownership:
        """
        Registra um modulo para ser rastreado pelo job diario, mesmo sem owner conhecido.
        Tenta consultar GitHub agora; se falhar, cria entrada placeholder com confianca=0.
        """
        pass

    @abstractmethod
    def refrescar_todos(self) -> ResultadoRefresh:
        """
        Consulta o GitHub para cada ownership ja persistido e atualiza o cache.
        Usado pelo job diario (US PU-02). Nao levanta — colhe erros no resumo.
        """
        pass
