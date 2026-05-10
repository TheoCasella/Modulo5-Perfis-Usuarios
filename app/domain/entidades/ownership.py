# Entidade de dominio: Ownership
# Representa o "dono" de um modulo dentro de um repositorio — quem mais contribui (commits).
# PU-09 cuida da resiliencia (cache + fallback).
# PU-02 vai refinar a identificacao (volume de contribuicao + job diario).

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Ownership:
    repositorio: str          # ex: "fnavai/Modulo5-Interface-e-Nuvem"
    modulo: str               # ex: "app/adapters/driving/http/saude_routes.py"
    owner_id: str             # login do GitHub ou email
    confianca: float          # 0..1 — fracao de commits desse owner sobre o total
    total_commits: int = 0    # total de commits considerados
    ultima_atualizacao: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "repositorio": self.repositorio,
            "modulo": self.modulo,
            "owner_id": self.owner_id,
            "confianca": round(self.confianca, 4),
            "total_commits": self.total_commits,
            "ultima_atualizacao": self.ultima_atualizacao.isoformat(),
        }

    def idade_segundos(self, agora: datetime | None = None) -> int:
        agora = agora or datetime.now(timezone.utc)
        return int((agora - self.ultima_atualizacao).total_seconds())
