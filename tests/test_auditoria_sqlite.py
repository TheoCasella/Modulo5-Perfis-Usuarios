# Testes do RepositorioAuditoriaSQLite — sobrevive a "restart" simulado.

from datetime import datetime, timezone

import pytest

from app.adapters.driven.persistence.repositorio_auditoria_sqlite import (
    RepositorioAuditoriaSQLite,
)
from app.domain.entidades.registro_auditoria import (
    FiltroAuditoria,
    RegistroAuditoria,
    TipoAcao,
)


@pytest.fixture
def caminho_db(tmp_path):
    return str(tmp_path / "auditoria_test.db")


def _registro(usuario="u1", acao=TipoAcao.VISUALIZOU, recurso_id="r1"):
    return RegistroAuditoria(
        usuario_id=usuario,
        tipo_acao=acao,
        tipo_recurso="documento",
        recurso_id=recurso_id,
        detalhes={"ip": "127.0.0.1"},
    )


def test_registrar_e_consultar_round_trip(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    repo.registrar(_registro())
    res = repo.consultar(FiltroAuditoria())
    assert len(res) == 1
    assert res[0].detalhes == {"ip": "127.0.0.1"}
    assert res[0].tipo_acao == TipoAcao.VISUALIZOU
    repo.fechar()


def test_persiste_apos_reabrir_conexao(caminho_db):
    repo1 = RepositorioAuditoriaSQLite(caminho_db)
    r = _registro(usuario="alice")
    repo1.registrar(r)
    repo1.fechar()

    repo2 = RepositorioAuditoriaSQLite(caminho_db)
    res = repo2.consultar(FiltroAuditoria(usuario_id="alice"))
    assert len(res) == 1
    assert res[0].id == r.id
    repo2.fechar()


def test_id_duplicado_falha(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    r = _registro()
    repo.registrar(r)
    with pytest.raises(ValueError):
        repo.registrar(r)
    repo.fechar()


def test_filtros_combinados(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    repo.registrar(_registro(usuario="alice", acao=TipoAcao.VISUALIZOU, recurso_id="doc-1"))
    repo.registrar(_registro(usuario="alice", acao=TipoAcao.EDITOU, recurso_id="doc-1"))
    repo.registrar(_registro(usuario="bob", acao=TipoAcao.VISUALIZOU, recurso_id="doc-2"))

    res = repo.consultar(FiltroAuditoria(usuario_id="alice", tipo_acao=TipoAcao.EDITOU))
    assert len(res) == 1
    assert res[0].usuario_id == "alice"
    assert res[0].tipo_acao == TipoAcao.EDITOU
    repo.fechar()


def test_filtro_por_tempo(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    repo.registrar(_registro())
    futuro = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)
    res = repo.consultar(FiltroAuditoria(desde=futuro))
    assert res == []
    repo.fechar()


def test_limite_aplicado(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    for i in range(5):
        repo.registrar(_registro(recurso_id=f"r-{i}"))
    res = repo.consultar(FiltroAuditoria(limite=3))
    assert len(res) == 3
    repo.fechar()


def test_repositorio_nao_expoe_metodos_de_mutacao(caminho_db):
    repo = RepositorioAuditoriaSQLite(caminho_db)
    # Garantia de design: o port nao expoe update/delete.
    assert not hasattr(repo, "atualizar")
    assert not hasattr(repo, "remover")
    assert not hasattr(repo, "deletar")
    repo.fechar()
