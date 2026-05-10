# Entidade de dominio: RegistroAuditoria
# Append-only por design — frozen=True garante imutabilidade do objeto em memoria,
# e o repositorio nao expoe metodos de update/delete (US PU-06).

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class TipoAcao(Enum):
    VISUALIZOU = "visualizou"
    EDITOU = "editou"
    CRIOU = "criou"
    EXCLUIU = "excluiu"
    APROVOU = "aprovou"
    REJEITOU = "rejeitou"
    COMENTOU = "comentou"
    ATRIBUIU_PAPEL = "atribuiu_papel"
    REVOGOU_PAPEL = "revogou_papel"
    OUTRO = "outro"


@dataclass(frozen=True)
class RegistroAuditoria:
    usuario_id: str
    tipo_acao: TipoAcao
    tipo_recurso: str
    recurso_id: str
    detalhes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "tipo_acao": self.tipo_acao.value,
            "tipo_recurso": self.tipo_recurso,
            "recurso_id": self.recurso_id,
            "timestamp": self.timestamp.isoformat(),
            "detalhes": dict(self.detalhes),
        }


@dataclass(frozen=True)
class FiltroAuditoria:
    usuario_id: Optional[str] = None
    tipo_acao: Optional[TipoAcao] = None
    tipo_recurso: Optional[str] = None
    recurso_id: Optional[str] = None
    desde: Optional[datetime] = None  # inclusive
    ate: Optional[datetime] = None    # inclusive
    limite: int = 100
