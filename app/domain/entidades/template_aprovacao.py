# Entidade de dominio: TemplateAprovacao (US PU-04)
# Define quais papeis precisam aprovar um tipo de documento dentro de um projeto,
# e em que ordem (sequencial / paralelo / qualquer um).

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Tuple
import uuid


class NomePapel(Enum):
    TECH_LEAD = "tech_lead"
    PRODUCT_MANAGER = "product_manager"
    DESENVOLVEDOR = "desenvolvedor"
    GERENTE = "gerente"
    APROVADOR = "aprovador"
    REVISOR = "revisor"
    AUTOR = "autor"


class TipoFluxo(Enum):
    # Cada papel aprova na ordem listada — proximo so age depois do anterior.
    SEQUENCIAL = "sequencial"
    # Todos os papeis precisam aprovar, em qualquer ordem.
    PARALELO = "paralelo"
    # Basta um aprovar (any-of-N) para o doc ser considerado aprovado.
    QUALQUER_UM = "qualquer_um"


@dataclass(frozen=True)
class TemplateAprovacao:
    projeto_id: str
    tipo_documento: str  # ex: "ADR", "RFC", "Especificacao"
    papeis_aprovadores: Tuple[NomePapel, ...]
    fluxo: TipoFluxo = TipoFluxo.SEQUENCIAL
    ativo: bool = True
    criado_por: str = "system"
    atualizado_por: str = "system"
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    atualizado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projeto_id": self.projeto_id,
            "tipo_documento": self.tipo_documento,
            "papeis_aprovadores": [p.value for p in self.papeis_aprovadores],
            "fluxo": self.fluxo.value,
            "ativo": self.ativo,
            "criado_por": self.criado_por,
            "atualizado_por": self.atualizado_por,
            "criado_em": self.criado_em.isoformat(),
            "atualizado_em": self.atualizado_em.isoformat(),
        }
