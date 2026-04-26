# Entidade de dominio: Papel
# Responsabilidade: representar um papel de acesso no sistema.
# Não conhece banco, Flask, nem nenhuma tecnologia externa.

from dataclasses import dataclass
from enum import Enum


class NomePapel(Enum):
    VISUALIZADOR = "visualizador"
    EDITOR = "editor"
    APROVADOR = "aprovador"
    ADMIN = "admin"


@dataclass # @dataclass gera automaticamente __init__, __repr__ e __eq__ com base nos atributos declarados.
class Papel:
    id: int
    nome: NomePapel

    def pode_editar(self) -> bool:
        return self.nome in (NomePapel.EDITOR, NomePapel.APROVADOR, NomePapel.ADMIN)

    def pode_aprovar(self) -> bool:
        return self.nome in (NomePapel.APROVADOR, NomePapel.ADMIN)

    def pode_administrar(self) -> bool:
        return self.nome == NomePapel.ADMIN