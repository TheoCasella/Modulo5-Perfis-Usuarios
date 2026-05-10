# Porta driven: RepositorioOwnership
# Persistencia do ultimo ownership conhecido por (repositorio, modulo).
# Usado como fallback quando o GitHub esta fora (US PU-09).

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entidades.ownership import Ownership


class RepositorioOwnership(ABC):

    @abstractmethod
    def salvar(self, ownership: Ownership) -> None:
        """Insere ou atualiza (upsert por repositorio+modulo)."""
        pass

    @abstractmethod
    def obter(self, repositorio: str, modulo: str) -> Optional[Ownership]:
        """Retorna o ultimo registro conhecido — qualquer idade."""
        pass

    @abstractmethod
    def listar(self, repositorio: Optional[str] = None) -> List[Ownership]:
        """Lista ownerships conhecidos, opcionalmente filtrando por repositorio."""
        pass
