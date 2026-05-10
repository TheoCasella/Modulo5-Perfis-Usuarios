# Porta driving: NotificacaoService (US PU-07)
# Tambem serve como contrato de "notificador" injetado em outros services
# que disparam eventos (ex: AprovacaoService chama notificar_evento).

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entidades.notificacao import (
    Notificacao,
    Subscricao,
    TipoEventoNotificacao,
)


class NotificacaoService(ABC):

    # --- Seguir / parar de seguir ---

    @abstractmethod
    def seguir(self, usuario_id: str, documento_id: str) -> Subscricao:
        pass

    @abstractmethod
    def parar_de_seguir(self, usuario_id: str, documento_id: str) -> bool:
        pass

    @abstractmethod
    def listar_seguidores(self, documento_id: str) -> List[str]:
        pass

    @abstractmethod
    def listar_seguidos(self, usuario_id: str) -> List[Subscricao]:
        pass

    @abstractmethod
    def usuario_segue(self, usuario_id: str, documento_id: str) -> bool:
        pass

    # --- Disparo de evento (chamado por outros services tipo AprovacaoService) ---

    @abstractmethod
    def notificar_evento(
        self,
        documento_id: str,
        tipo: TipoEventoNotificacao,
        titulo: str,
        descricao: str = "",
        detalhes: Optional[Dict[str, Any]] = None,
        excluir_usuario: Optional[str] = None,
    ) -> int:
        """
        Cria uma Notificacao para cada seguidor do documento.
        `excluir_usuario`: nao notifica esse usuario (tipico: nao notificar o ator do evento).
        Retorna quantos foram notificados.
        """
        pass

    # --- Caixa de entrada do usuario ---

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
    def marcar_como_lida(self, usuario_id: str, notificacao_id: str) -> Notificacao:
        """Levanta NotificacaoNaoEncontradaError se nao existir ou nao pertencer ao usuario."""
        pass

    @abstractmethod
    def marcar_todas_como_lidas(self, usuario_id: str) -> int:
        pass
