# Porta driven: RepositorioDocumentos (US PU-05)

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entidades.aprovacao import DocumentoSubmetido, StatusAprovacao


class RepositorioDocumentos(ABC):

    @abstractmethod
    def salvar(self, documento: DocumentoSubmetido) -> None:
        """Insere ou atualiza por id."""
        pass

    @abstractmethod
    def obter(self, documento_id: str) -> Optional[DocumentoSubmetido]:
        pass

    @abstractmethod
    def listar(
        self,
        projeto_id: Optional[str] = None,
        status: Optional[StatusAprovacao] = None,
    ) -> List[DocumentoSubmetido]:
        pass
