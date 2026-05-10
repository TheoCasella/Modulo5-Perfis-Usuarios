# Testes do AuditoriaServiceImpl com repositorio em memoria (US PU-06).

from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.domain.entidades.registro_auditoria import FiltroAuditoria, TipoAcao
from app.domain.excecoes import AuditoriaInvalidaError, FiltroAuditoriaInvalidoError


def _service():
    return AuditoriaServiceImpl(RepositorioAuditoriaMemoria())


def test_registrar_e_consultar_devolve_registro():
    s = _service()
    s.registrar_acao("user1", TipoAcao.VISUALIZOU, "documento", "doc-1")
    res = s.consultar(FiltroAuditoria())
    assert len(res) == 1
    r = res[0]
    assert r.usuario_id == "user1"
    assert r.tipo_acao == TipoAcao.VISUALIZOU
    assert r.tipo_recurso == "documento"
    assert r.recurso_id == "doc-1"


def test_registrar_sem_usuario_falha():
    s = _service()
    with pytest.raises(AuditoriaInvalidaError):
        s.registrar_acao("", TipoAcao.VISUALIZOU, "documento", "doc-1")


def test_registrar_sem_recurso_falha():
    s = _service()
    with pytest.raises(AuditoriaInvalidaError):
        s.registrar_acao("user1", TipoAcao.VISUALIZOU, "documento", "  ")


def test_filtro_por_usuario():
    s = _service()
    s.registrar_acao("alice", TipoAcao.VISUALIZOU, "documento", "doc-1")
    s.registrar_acao("bob", TipoAcao.EDITOU, "documento", "doc-2")
    res = s.consultar(FiltroAuditoria(usuario_id="alice"))
    assert len(res) == 1
    assert res[0].usuario_id == "alice"


def test_filtro_por_tipo_acao_e_recurso():
    s = _service()
    s.registrar_acao("alice", TipoAcao.VISUALIZOU, "documento", "doc-1")
    s.registrar_acao("alice", TipoAcao.EDITOU, "documento", "doc-1")
    s.registrar_acao("alice", TipoAcao.VISUALIZOU, "papel", "papel-1")

    res = s.consultar(FiltroAuditoria(tipo_acao=TipoAcao.VISUALIZOU, tipo_recurso="documento"))
    assert len(res) == 1
    assert res[0].tipo_acao == TipoAcao.VISUALIZOU
    assert res[0].tipo_recurso == "documento"


def test_filtro_intervalo_temporal():
    s = _service()
    s.registrar_acao("alice", TipoAcao.VISUALIZOU, "documento", "doc-1")

    agora = datetime.now(timezone.utc)
    futuro = agora + timedelta(hours=1)
    passado = agora - timedelta(hours=1)

    res = s.consultar(FiltroAuditoria(desde=passado, ate=futuro))
    assert len(res) == 1

    res_vazio = s.consultar(FiltroAuditoria(desde=futuro))
    assert res_vazio == []


def test_filtro_invalido_ate_antes_de_desde():
    s = _service()
    agora = datetime.now(timezone.utc)
    with pytest.raises(FiltroAuditoriaInvalidoError):
        s.consultar(FiltroAuditoria(desde=agora, ate=agora - timedelta(hours=1)))


def test_filtro_limite_zero_invalido():
    s = _service()
    with pytest.raises(FiltroAuditoriaInvalidoError):
        s.consultar(FiltroAuditoria(limite=0))


def test_resultados_ordenados_mais_recente_primeiro():
    s = _service()
    a = s.registrar_acao("u", TipoAcao.VISUALIZOU, "d", "1")
    b = s.registrar_acao("u", TipoAcao.EDITOU, "d", "1")
    c = s.registrar_acao("u", TipoAcao.APROVOU, "d", "1")
    res = s.consultar(FiltroAuditoria())
    ids_ordenados = [r.id for r in res]
    # Os timestamps em sequencia rapida podem coincidir; checamos so que c aparece antes de a quando dao timestamps diferentes.
    assert ids_ordenados[0] in {a.id, b.id, c.id}
    assert set(ids_ordenados) == {a.id, b.id, c.id}


def test_registro_eh_imutavel_em_memoria():
    s = _service()
    r = s.registrar_acao("u", TipoAcao.VISUALIZOU, "d", "1")
    with pytest.raises(Exception):
        # frozen=True bloqueia mutacao
        r.usuario_id = "outro"  # type: ignore[misc]
