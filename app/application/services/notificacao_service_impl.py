# Implementacao do NotificacaoService (US PU-07).

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.application.ports.driven.repositorio_notificacoes import (
    RepositorioNotificacoes,
)
from app.application.ports.driving.notificacao_service import NotificacaoService
from app.domain.entidades.notificacao import (
    Notificacao,
    Subscricao,
    TipoEventoNotificacao,
)
from app.domain.excecoes import (
    NotificacaoInvalidaError,
    NotificacaoNaoEncontradaError,
)


class NotificacaoServiceImpl(NotificacaoService):

    def __init__(self, repositorio: RepositorioNotificacoes):
        self._repo = repositorio

    # --- Seguir / parar de seguir ---

    def seguir(self, usuario_id: str, documento_id: str) -> Subscricao:
        usuario = self._exigir_string("usuario_id", usuario_id)
        documento = self._exigir_string("documento_id", documento_id)
        sub = Subscricao(usuario_id=usuario, documento_id=documento)
        self._repo.adicionar_subscricao(sub)
        return sub

    def parar_de_seguir(self, usuario_id: str, documento_id: str) -> bool:
        return self._repo.remover_subscricao(usuario_id, documento_id)

    def listar_seguidores(self, documento_id: str) -> List[str]:
        return self._repo.listar_seguidores(documento_id)

    def listar_seguidos(self, usuario_id: str) -> List[Subscricao]:
        return self._repo.listar_seguidos(usuario_id)

    def usuario_segue(self, usuario_id: str, documento_id: str) -> bool:
        return self._repo.usuario_segue(usuario_id, documento_id)

    # --- Disparo de evento ---

    def notificar_evento(
        self,
        documento_id: str,
        tipo: TipoEventoNotificacao,
        titulo: str,
        descricao: str = "",
        detalhes: Optional[Dict[str, Any]] = None,
        excluir_usuario: Optional[str] = None,
    ) -> int:
        if not documento_id or not documento_id.strip():
            raise NotificacaoInvalidaError("documento_id e obrigatorio.")
        if not titulo or not titulo.strip():
            raise NotificacaoInvalidaError("titulo e obrigatorio.")

        seguidores = self._repo.listar_seguidores(documento_id)
        if excluir_usuario:
            seguidores = [s for s in seguidores if s != excluir_usuario]

        for seguidor in seguidores:
            notificacao = Notificacao(
                usuario_id=seguidor,
                documento_id=documento_id,
                tipo_evento=tipo,
                titulo=titulo.strip(),
                descricao=(descricao or "").strip(),
                detalhes=dict(detalhes or {}),
            )
            self._repo.salvar_notificacao(notificacao)
        return len(seguidores)

    # --- Caixa de entrada ---

    def listar_notificacoes(
        self,
        usuario_id: str,
        lida: Optional[bool] = None,
        documento_id: Optional[str] = None,
        limite: int = 50,
    ) -> List[Notificacao]:
        return self._repo.listar_notificacoes(
            usuario_id=usuario_id, lida=lida,
            documento_id=documento_id, limite=limite,
        )

    def contar_nao_lidas(self, usuario_id: str) -> int:
        return self._repo.contar_nao_lidas(usuario_id)

    def marcar_como_lida(self, usuario_id: str, notificacao_id: str) -> Notificacao:
        notificacao = self._repo.obter_notificacao(notificacao_id)
        if notificacao is None or notificacao.usuario_id != usuario_id:
            raise NotificacaoNaoEncontradaError(
                f"Notificacao {notificacao_id} nao existe para usuario {usuario_id}."
            )
        if notificacao.lida:
            return notificacao
        atualizada = replace(
            notificacao, lida=True, lida_em=datetime.now(timezone.utc),
        )
        self._repo.salvar_notificacao(atualizada)
        return atualizada

    def marcar_todas_como_lidas(self, usuario_id: str) -> int:
        return self._repo.marcar_todas_como_lidas(usuario_id)

    # --- Helpers ---

    @staticmethod
    def _exigir_string(nome: str, valor: str) -> str:
        if not valor or not valor.strip():
            raise NotificacaoInvalidaError(f"campo '{nome}' e obrigatorio.")
        return valor.strip()
