# Porta driven: RepositorioAprovacoes (US PU-05)
# Append-only: cada decisao eh um registro novo. Sem update/delete.

from abc import ABC, abstractmethod
from typing import List

from app.domain.entidades.aprovacao import Aprovacao


class RepositorioAprovacoes(ABC):

    @abstractmethod
    def registrar(self, aprovacao: Aprovacao) -> None:
        pass

    @abstractmethod
    def listar_por_documento(self, documento_id: str) -> List[Aprovacao]:
        pass
