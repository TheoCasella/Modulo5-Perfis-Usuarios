# Porta driven: RepositorioNotificacoes (US PU-07)
# Cobre subscricoes (seguidores) e notificacoes individuais — duas tabelas.

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entidades.notificacao import Notificacao, Subscricao


class RepositorioNotificacoes(ABC):

    # --- Subscricoes (quem segue o que) ---

    @abstractmethod
    def adicionar_subscricao(self, subscricao: Subscricao) -> None:
        """Levanta SubscricaoDuplicadaError se ja existir."""
        pass

    @abstractmethod
    def remover_subscricao(self, usuario_id: str, documento_id: str) -> bool:
        pass

    @abstractmethod
    def listar_seguidores(self, documento_id: str) -> List[str]:
        """IDs de usuarios que seguem o documento."""
        pass

    @abstractmethod
    def listar_seguidos(self, usuario_id: str) -> List[Subscricao]:
        pass

    @abstractmethod
    def usuario_segue(self, usuario_id: str, documento_id: str) -> bool:
        pass

    # --- Notificacoes (entradas individuais por usuario+evento) ---

    @abstractmethod
    def salvar_notificacao(self, notificacao: Notificacao) -> None:
        """Insere ou atualiza por id (usado tambem para marcar como lida)."""
        pass

    @abstractmethod
    def obter_notificacao(self, notificacao_id: str) -> Optional[Notificacao]:
        pass

    @abstractmethod
    def listar_notificacoes(
        self,
        usuario_id: str,
        lida: Optional[bool] = None,
        documento_id: Optional[str] = None,
        limite: int = 50,
    ) -> List[Notificacao]:
        pass

    @abstractmethod
    def contar_nao_lidas(self, usuario_id: str) -> int:
        pass

    @abstractmethod
    def marcar_todas_como_lidas(self, usuario_id: str) -> int:
        """Retorna quantas foram marcadas."""
        pass
