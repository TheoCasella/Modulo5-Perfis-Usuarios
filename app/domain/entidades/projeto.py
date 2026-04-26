# Entidade de domínio: Projeto
# Responsabilidade: representar o escopo onde papés e atribatribuiçõesuicoes existem.

from dataclasses import dataclass


@dataclass
class Projeto:
    id: str
    nome: str