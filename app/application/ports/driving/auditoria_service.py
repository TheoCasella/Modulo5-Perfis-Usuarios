# Porta driving: AuditoriaService
# Caso de uso: registrar e consultar acoes para compliance (US PU-06).

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entidades.registro_auditoria import (
    FiltroAuditoria,
    RegistroAuditoria,
    TipoAcao,
)


class AuditoriaService(ABC):

    @abstractmethod
    def registrar_acao(
        self,
        usuario_id: str,
        tipo_acao: TipoAcao,
        tipo_recurso: str,
        recurso_id: str,
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> RegistroAuditoria:
        """Cria um RegistroAuditoria e persiste. Levanta AuditoriaInvalidaError em campos vazios."""
        pass

    @abstractmethod
    def consultar(self, filtros: FiltroAuditoria) -> List[RegistroAuditoria]:
        """Consulta com filtros — mais recentes primeiro."""
        pass
