# Porta driven: RepositorioAuditoria
# Append-only por design — sem metodos de update/delete (US PU-06).

from abc import ABC, abstractmethod
from typing import List

from app.domain.entidades.registro_auditoria import FiltroAuditoria, RegistroAuditoria


class RepositorioAuditoria(ABC):

    @abstractmethod
    def registrar(self, registro: RegistroAuditoria) -> None:
        """Persiste um registro novo. Falha se id ja existir."""
        pass

    @abstractmethod
    def consultar(self, filtros: FiltroAuditoria) -> List[RegistroAuditoria]:
        """Retorna registros que casam com os filtros, mais recentes primeiro."""
        pass
