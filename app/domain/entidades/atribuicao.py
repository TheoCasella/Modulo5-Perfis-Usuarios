# Entidade de domínio: Atribuição
# Responsabilidade: vincular um usuário a um papel dentro de um projeto.
# Regra de domínio: um usuário pode ter papéis diferentes em projetos diferentes.

from dataclasses import dataclass
from datetime import datetime
from app.domain.entidades.papel import NomePapel


@dataclass
class Atribuicao:
    id: int
    usuario_id: str
    projeto_id: str
    nome_papel: NomePapel
    criada_em: datetime

    def pertence_ao_projeto(self, projeto_id: str) -> bool:
        return self.projeto_id == projeto_id

    def tem_papel(self, nome_papel: NomePapel) -> bool:
        return self.nome_papel == nome_papel