# Entidade de domnínio: Usuário
# Responsabilidade: representar um usuário da plataforma.
# Referencia mínima — identidade completa vem do módulo de Gerenciamento.

from dataclasses import dataclass


@dataclass
class Usuario:
    id: str
    nome: str
    email: str