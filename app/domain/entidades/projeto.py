# Entidade de domínio: Projeto
# Responsabilidade: representar o escopo onde papéis e atribuições existem.

from dataclasses import dataclass


@dataclass
class Projeto:
    id: str
    nome: str