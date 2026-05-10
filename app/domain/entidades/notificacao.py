# Entidades de dominio para notificacoes in-app (US PU-07).

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class TipoEventoNotificacao(Enum):
    DOCUMENTO_SUBMETIDO = "documento_submetido"
    DOCUMENTO_APROVADO = "documento_aprovado"
    DOCUMENTO_REJEITADO = "documento_rejeitado"
    DOCUMENTO_CANCELADO = "documento_cancelado"
    DOCUMENTO_COMENTADO = "documento_comentado"
    DOCUMENTO_EDITADO = "documento_editado"
    OUTRO = "outro"


@dataclass(frozen=True)
class Subscricao:
    """Indica que `usuario_id` segue `documento_id` e quer ser notificado de eventos."""
    usuario_id: str
    documento_id: str
    criada_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usuario_id": self.usuario_id,
            "documento_id": self.documento_id,
            "criada_em": self.criada_em.isoformat(),
        }


@dataclass(frozen=True)
class Notificacao:
    usuario_id: str
    documento_id: str
    tipo_evento: TipoEventoNotificacao
    titulo: str
    descricao: str = ""
    detalhes: Dict[str, Any] = field(default_factory=dict)
    lida: bool = False
    criada_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lida_em: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "documento_id": self.documento_id,
            "tipo_evento": self.tipo_evento.value,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "detalhes": dict(self.detalhes),
            "lida": self.lida,
            "criada_em": self.criada_em.isoformat(),
            "lida_em": self.lida_em.isoformat() if self.lida_em else None,
        }
