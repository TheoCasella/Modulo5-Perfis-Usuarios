# Porta driven: RepositorioOwnershipDocumentos (US PU-03)

from abc import ABC, abstractmethod
from typing import List, Optional, Set

from app.domain.entidades.ownership_documento import OwnershipDocumento


class RepositorioOwnershipDocumentos(ABC):

    @abstractmethod
    def salvar(self, ownership: OwnershipDocumento) -> None:
        """Insere ou substitui (upsert por documento_id)."""
        pass

    @abstractmethod
    def obter(self, documento_id: str) -> Optional[OwnershipDocumento]:
        pass

    @abstractmethod
    def listar(self) -> List[OwnershipDocumento]:
        pass

    @abstractmethod
    def documentos_com_owner(self) -> Set[str]:
        """IDs de documentos que ja tem owner — util pra calcular o conjunto orfao."""
        pass

    @abstractmethod
    def remover(self, documento_id: str) -> bool:
        pass
