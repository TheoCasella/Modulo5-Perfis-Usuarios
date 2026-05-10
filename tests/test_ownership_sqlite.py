# Testes do RepositorioOwnershipSQLite (US PU-09).

from datetime import datetime, timezone

import pytest

from app.adapters.driven.persistence.repositorio_ownership_sqlite import (
    RepositorioOwnershipSQLite,
)
from app.domain.entidades.ownership import Ownership


@pytest.fixture
def caminho_db(tmp_path):
    return str(tmp_path / "ownership_test.db")


def _ownership(repo="r1", modulo="m1", owner="alice", confianca=0.8):
    return Ownership(
        repositorio=repo,
        modulo=modulo,
        owner_id=owner,
        confianca=confianca,
        total_commits=10,
        ultima_atualizacao=datetime.now(timezone.utc),
    )


def test_salvar_e_obter(caminho_db):
    repo = RepositorioOwnershipSQLite(caminho_db)
    repo.salvar(_ownership())
    encontrado = repo.obter("r1", "m1")
    assert encontrado is not None
    assert encontrado.owner_id == "alice"
    repo.fechar()


def test_obter_inexistente_devolve_none(caminho_db):
    repo = RepositorioOwnershipSQLite(caminho_db)
    assert repo.obter("r1", "m1") is None
    repo.fechar()


def test_upsert_atualiza_owner(caminho_db):
    repo = RepositorioOwnershipSQLite(caminho_db)
    repo.salvar(_ownership(owner="alice"))
    repo.salvar(_ownership(owner="bob", confianca=0.9))
    encontrado = repo.obter("r1", "m1")
    assert encontrado.owner_id == "bob"
    assert encontrado.confianca == pytest.approx(0.9)
    repo.fechar()


def test_persiste_apos_reabrir(caminho_db):
    r1 = RepositorioOwnershipSQLite(caminho_db)
    r1.salvar(_ownership(owner="alice"))
    r1.fechar()

    r2 = RepositorioOwnershipSQLite(caminho_db)
    encontrado = r2.obter("r1", "m1")
    assert encontrado is not None
    assert encontrado.owner_id == "alice"
    r2.fechar()


def test_listar_filtrando_por_repositorio(caminho_db):
    repo = RepositorioOwnershipSQLite(caminho_db)
    repo.salvar(_ownership(repo="r1", modulo="a", owner="alice"))
    repo.salvar(_ownership(repo="r1", modulo="b", owner="bob"))
    repo.salvar(_ownership(repo="r2", modulo="c", owner="carol"))

    todos = repo.listar()
    assert len(todos) == 3

    so_r1 = repo.listar(repositorio="r1")
    assert len(so_r1) == 2
    assert {o.owner_id for o in so_r1} == {"alice", "bob"}
    repo.fechar()
