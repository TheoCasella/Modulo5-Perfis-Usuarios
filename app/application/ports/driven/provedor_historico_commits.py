# Porta driven: ProvedorHistoricoCommits
# Abstrai a fonte de historico (GitHub, GitLab, mock). PU-02 vai expandir.

from abc import ABC, abstractmethod

from app.domain.entidades.ownership import Ownership


class ProvedorHistoricoCommits(ABC):

    @abstractmethod
    def identificar_owner(self, repositorio: str, modulo: str) -> Ownership:
        """
        Consulta a fonte e devolve quem mais commitou no modulo.
        Levanta GitHubIndisponivelError se a fonte nao responder.
        Levanta OwnershipNaoEncontradoError se o modulo nao tiver commits.
        """
        pass
