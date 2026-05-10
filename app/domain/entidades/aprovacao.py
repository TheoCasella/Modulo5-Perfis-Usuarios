# Entidades de dominio para o fluxo de aprovacao (US PU-05).

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple
import uuid

from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo


class StatusAprovacao(Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"
    CANCELADO = "cancelado"


class Decisao(Enum):
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"


@dataclass(frozen=True)
class Aprovacao:
    documento_id: str
    aprovador_id: str
    papel: NomePapel
    decisao: Decisao
    comentario: str = ""
    decidido_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "documento_id": self.documento_id,
            "aprovador_id": self.aprovador_id,
            "papel": self.papel.value,
            "decisao": self.decisao.value,
            "comentario": self.comentario,
            "decidido_em": self.decidido_em.isoformat(),
        }


@dataclass(frozen=True)
class DocumentoSubmetido:
    """
    Snapshot do template no momento da submissao — papeis_aprovadores e fluxo
    ficam congelados; mudancas posteriores no template nao afetam este doc.
    """
    id: str  # id do documento (informado pelo chamador)
    projeto_id: str
    tipo_documento: str
    autor_id: str
    titulo: str
    template_id: str
    papeis_aprovadores: Tuple[NomePapel, ...]
    fluxo: TipoFluxo
    status: StatusAprovacao = StatusAprovacao.PENDENTE
    submetido_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finalizado_em: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None

    def to_dict(self, decisoes: Optional[List[Aprovacao]] = None) -> dict:
        base = {
            "id": self.id,
            "projeto_id": self.projeto_id,
            "tipo_documento": self.tipo_documento,
            "autor_id": self.autor_id,
            "titulo": self.titulo,
            "template_id": self.template_id,
            "papeis_aprovadores": [p.value for p in self.papeis_aprovadores],
            "fluxo": self.fluxo.value,
            "status": self.status.value,
            "submetido_em": self.submetido_em.isoformat(),
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
            "motivo_cancelamento": self.motivo_cancelamento,
        }
        if decisoes is not None:
            base["decisoes"] = [d.to_dict() for d in decisoes]
            base["papeis_pendentes"] = [p.value for p in self.papeis_pendentes(decisoes)]
        return base

    # ------------------------------------------------------------------
    # Logica de negocio (avaliacao do fluxo)
    # ------------------------------------------------------------------

    def papeis_pendentes(self, decisoes: List[Aprovacao]) -> List[NomePapel]:
        """Quais papeis ainda precisam decidir? Considera o fluxo."""
        if self.status != StatusAprovacao.PENDENTE:
            return []

        ja_aprovaram = {d.papel for d in decisoes if d.decisao == Decisao.APROVADO}

        if self.fluxo == TipoFluxo.PARALELO:
            return [p for p in self.papeis_aprovadores if p not in ja_aprovaram]

        if self.fluxo == TipoFluxo.QUALQUER_UM:
            if ja_aprovaram & set(self.papeis_aprovadores):
                return []
            return list(self.papeis_aprovadores)

        # SEQUENCIAL: somente o proximo da fila esta pendente
        for papel in self.papeis_aprovadores:
            if papel not in ja_aprovaram:
                return [papel]
        return []

    def calcular_status(self, decisoes: List[Aprovacao]) -> StatusAprovacao:
        """Recalcula o status agregado a partir das decisoes existentes."""
        if self.status in (StatusAprovacao.CANCELADO,):
            return self.status

        rejeitou_alguem = any(d.decisao == Decisao.REJEITADO for d in decisoes)
        if rejeitou_alguem:
            # Rejeicao eh terminal em todos os fluxos (uma rejeicao basta).
            return StatusAprovacao.REJEITADO

        ja_aprovaram = {d.papel for d in decisoes if d.decisao == Decisao.APROVADO}
        papeis = set(self.papeis_aprovadores)

        if self.fluxo == TipoFluxo.QUALQUER_UM:
            return StatusAprovacao.APROVADO if ja_aprovaram & papeis else StatusAprovacao.PENDENTE

        # PARALELO e SEQUENCIAL exigem todos
        if ja_aprovaram >= papeis:
            return StatusAprovacao.APROVADO
        return StatusAprovacao.PENDENTE
