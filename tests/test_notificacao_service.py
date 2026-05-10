# Testes do NotificacaoServiceImpl (US PU-07).

import pytest

from app.adapters.driven.persistence.repositorio_notificacoes_sqlite import (
    RepositorioNotificacoesSQLite,
)
from app.application.services.notificacao_service_impl import NotificacaoServiceImpl
from app.domain.entidades.notificacao import TipoEventoNotificacao
from app.domain.excecoes import (
    NotificacaoInvalidaError,
    NotificacaoNaoEncontradaError,
    SubscricaoDuplicadaError,
)


@pytest.fixture
def service(tmp_path):
    repo = RepositorioNotificacoesSQLite(str(tmp_path / "notif.db"))
    yield NotificacaoServiceImpl(repo)
    repo.fechar()


def test_seguir_e_listar_seguidores(service):
    service.seguir("alice", "doc-1")
    service.seguir("bob", "doc-1")
    seguidores = service.listar_seguidores("doc-1")
    assert set(seguidores) == {"alice", "bob"}


def test_seguir_duplicado_falha(service):
    service.seguir("alice", "doc-1")
    with pytest.raises(SubscricaoDuplicadaError):
        service.seguir("alice", "doc-1")


def test_seguir_campos_vazios_falha(service):
    with pytest.raises(NotificacaoInvalidaError):
        service.seguir("", "doc-1")
    with pytest.raises(NotificacaoInvalidaError):
        service.seguir("alice", "")


def test_parar_de_seguir(service):
    service.seguir("alice", "doc-1")
    assert service.parar_de_seguir("alice", "doc-1") is True
    assert service.parar_de_seguir("alice", "doc-1") is False
    assert service.listar_seguidores("doc-1") == []


def test_listar_seguidos(service):
    service.seguir("alice", "doc-1")
    service.seguir("alice", "doc-2")
    service.seguir("bob", "doc-1")
    seguidos_alice = service.listar_seguidos("alice")
    assert {s.documento_id for s in seguidos_alice} == {"doc-1", "doc-2"}


def test_usuario_segue(service):
    service.seguir("alice", "doc-1")
    assert service.usuario_segue("alice", "doc-1") is True
    assert service.usuario_segue("alice", "doc-2") is False


def test_notificar_evento_cria_notificacoes_para_seguidores(service):
    service.seguir("alice", "doc-1")
    service.seguir("bob", "doc-1")
    service.seguir("carol", "doc-2")  # noise

    n = service.notificar_evento(
        documento_id="doc-1",
        tipo=TipoEventoNotificacao.DOCUMENTO_APROVADO,
        titulo="Doc aprovado",
        descricao="lgtm",
    )
    assert n == 2
    notif_alice = service.listar_notificacoes("alice")
    notif_carol = service.listar_notificacoes("carol")
    assert len(notif_alice) == 1
    assert notif_alice[0].titulo == "Doc aprovado"
    assert notif_alice[0].tipo_evento == TipoEventoNotificacao.DOCUMENTO_APROVADO
    assert len(notif_carol) == 0  # carol nao segue doc-1


def test_notificar_evento_excluir_usuario(service):
    """O ator do evento normalmente nao se notifica — mesmo que esteja seguindo."""
    service.seguir("alice", "doc-1")
    service.seguir("bob", "doc-1")
    n = service.notificar_evento(
        documento_id="doc-1",
        tipo=TipoEventoNotificacao.DOCUMENTO_EDITADO,
        titulo="X",
        excluir_usuario="alice",
    )
    assert n == 1
    assert len(service.listar_notificacoes("alice")) == 0
    assert len(service.listar_notificacoes("bob")) == 1


def test_notificar_evento_titulo_vazio_falha(service):
    with pytest.raises(NotificacaoInvalidaError):
        service.notificar_evento("doc", TipoEventoNotificacao.OUTRO, "")


def test_marcar_como_lida(service):
    service.seguir("alice", "doc-1")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "X")
    notif = service.listar_notificacoes("alice")[0]
    assert notif.lida is False

    atualizada = service.marcar_como_lida("alice", notif.id)
    assert atualizada.lida is True
    assert atualizada.lida_em is not None


def test_marcar_lida_de_outro_usuario_404(service):
    service.seguir("alice", "doc-1")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "X")
    notif = service.listar_notificacoes("alice")[0]
    with pytest.raises(NotificacaoNaoEncontradaError):
        service.marcar_como_lida("bob", notif.id)


def test_marcar_lida_inexistente_404(service):
    with pytest.raises(NotificacaoNaoEncontradaError):
        service.marcar_como_lida("alice", "id-fake")


def test_marcar_todas_como_lidas(service):
    service.seguir("alice", "doc-1")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "A")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "B")
    assert service.contar_nao_lidas("alice") == 2
    n = service.marcar_todas_como_lidas("alice")
    assert n == 2
    assert service.contar_nao_lidas("alice") == 0


def test_filtrar_por_lida_e_documento(service):
    service.seguir("alice", "doc-1")
    service.seguir("alice", "doc-2")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "A")
    service.notificar_evento("doc-2", TipoEventoNotificacao.OUTRO, "B")

    so_doc_1 = service.listar_notificacoes("alice", documento_id="doc-1")
    assert len(so_doc_1) == 1
    assert so_doc_1[0].documento_id == "doc-1"

    so_nao_lidas = service.listar_notificacoes("alice", lida=False)
    assert len(so_nao_lidas) == 2


def test_contar_nao_lidas(service):
    service.seguir("alice", "doc-1")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "A")
    service.notificar_evento("doc-1", TipoEventoNotificacao.OUTRO, "B")
    assert service.contar_nao_lidas("alice") == 2
    notif = service.listar_notificacoes("alice")[0]
    service.marcar_como_lida("alice", notif.id)
    assert service.contar_nao_lidas("alice") == 1
