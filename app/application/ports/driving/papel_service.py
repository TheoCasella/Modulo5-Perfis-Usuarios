# Porta driving: PapelService
# Responsabilidade: descrever as operações de gerenciamento de papéis que o núcleo expoe para o mundo externo.
# Não implementa nada — define o contrato --> trtam-se de interfaces.

from abc import ABC, abstractmethod
from typing import List
from app.domain.entidades.papel import NomePapel
from app.domain.entidades.atribuicao import Atribuicao


class PapelService(ABC):

    @abstractmethod
    def atribuir_papel(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> Atribuicao:
        """
        Atribui um papel a um usuario dentro de um projeto.
        Levanta AtribuicaoDuplicadaError se o usuario ja tem o papel.
        """
        pass

    @abstractmethod
    def revogar_papel(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> None:
        """
        Revoga um papel de um usuario dentro de um projeto.
        Levanta AtribuicaoNaoEncontradaError se nao existir.
        """
        pass

    @abstractmethod
    def verificar_permissao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> bool:
        """
        Verifica se usuario tem pelo menos o papel informado no projeto.
        Retorna True se tiver, False se nao tiver.
        Nao levanta excecao — decisao de negar acesso e do chamador.
        """
        pass

    @abstractmethod
    def listar_papeis_do_usuario(
        self,
        usuario_id: str,
        projeto_id: str
    ) -> List[Atribuicao]:
        """
        Lista todas as atribuicoes de um usuario em um projeto.
        Retorna lista vazia se nao tiver nenhuma.
        """
        pass

    @abstractmethod
    def listar_usuarios_do_projeto(
        self,
        projeto_id: str
    ) -> List[Atribuicao]:
        """
        Lista todas as atribuicoes de todos os usuarios em um projeto.
        """
        pass