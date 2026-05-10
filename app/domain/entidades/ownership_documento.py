# Entidades de dominio para ownership de documentos (US PU-03).

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FonteOwnership(Enum):
    MANUAL = "manual"                  # alguem atribuiu explicitamente
    SUGESTAO_ACEITA = "sugestao_aceita"  # vem de uma sugestao automatica que foi aprovada


@dataclass(frozen=True)
class OwnershipDocumento:
    documento_id: str
    owner_id: str
    atribuido_por: str       # quem aprovou/decidiu
    fonte: FonteOwnership = FonteOwnership.MANUAL
    motivo: str = ""
    atribuido_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documento_id": self.documento_id,
            "owner_id": self.owner_id,
            "atribuido_por": self.atribuido_por,
            "fonte": self.fonte.value,
            "motivo": self.motivo,
            "atribuido_em": self.atribuido_em.isoformat(),
        }


@dataclass(frozen=True)
class CandidatoOwner:
    """Um possivel owner com pontuacao baseada em sinais historicos."""
    usuario_id: str
    score: int               # quantidade ponderada de sinais (criou=3, editou=2, comentou=1)
    eventos_considerados: int  # total de eventos do usuario contados
    motivo: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usuario_id": self.usuario_id,
            "score": self.score,
            "eventos_considerados": self.eventos_considerados,
            "motivo": self.motivo,
        }


@dataclass(frozen=True)
class SugestaoOwnership:
    """Resultado da analise heuristica para sugerir owner — nao persistido, calculado on demand."""
    documento_id: str
    candidato_principal: Optional[CandidatoOwner]
    candidatos_alternativos: Tuple[CandidatoOwner, ...] = ()
    explicacao: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documento_id": self.documento_id,
            "candidato_principal": self.candidato_principal.to_dict() if self.candidato_principal else None,
            "candidatos_alternativos": [c.to_dict() for c in self.candidatos_alternativos],
            "explicacao": self.explicacao,
        }
