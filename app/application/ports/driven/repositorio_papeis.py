# Porta driven: RepositorioPapeis
# Responsabilidade: descrever o contrato de persistência de papéis e atribuições. 
# O nucleo depende desta interface, nunca da implementação.

from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entidades.papel import NomePapel
from app.domain.entidades.atribuicao import Atribuicao


class RepositorioPapeis(ABC):

    @abstractmethod
    def salvar_atribuicao(self, atribuicao: Atribuicao) -> Atribuicao:
        """
        Persiste uma nova atribuicao.
        Levanta AtribuicaoDuplicadaError se ja existir.
        """
        pass

    @abstractmethod
    def remover_atribuicao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> None:
        """
        Remove uma atribuicao existente.
        Levanta AtribuicaoNaoEncontradaError se nao encontrar.
        """
        pass

    @abstractmethod
    def buscar_atribuicao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> Optional[Atribuicao]: # 'Optional[Atribuicao] não é necessariamente um erro, pode ser None se não encontrar
        """
        Busca uma atribuicao especifica.
        Retorna None se nao encontrar (nao levanta excecao).
        """
        pass

    @abstractmethod
    def listar_por_usuario_e_projeto(
        self,
        usuario_id: str,
        projeto_id: str
    ) -> List[Atribuicao]:
        """
        Lista todas as atribuicoes de um usuario em um projeto.
        """
        pass

    @abstractmethod
    def listar_por_projeto(
        self,
        projeto_id: str
    ) -> List[Atribuicao]:
        """
        Lista todas as atribuicoes de todos os usuarios em um projeto.
        """
        pass

    @abstractmethod
    def verificar_existencia(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> bool:
        """
        Verifica se uma atribuicao existe sem retornar o objeto completo.
        Mais eficiente que buscar_atribuicao quando so precisa do booleano.
        """
        pass