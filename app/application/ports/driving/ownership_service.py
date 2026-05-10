# Porta driving: OwnershipService
# Caso de uso: identificar owner de um modulo de forma resiliente (US PU-09).

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class OwnershipService(ABC):

    @abstractmethod
    def obter_owner(self, repositorio: str, modulo: str) -> RespostaOwnership:
        """
        Tenta GitHub; em falha, cai no ultimo registro conhecido.
        Levanta OwnershipNaoEncontradoError se nao houver nem cache nem GitHub.
        """
        pass

    @abstractmethod
    def listar_owners_conhecidos(self, repositorio: Optional[str] = None) -> List[Ownership]:
        """Lista ownerships ja persistidos (so cache, sem chamada externa)."""
        pass
