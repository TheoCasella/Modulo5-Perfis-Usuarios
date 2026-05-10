# Testes do RepositorioTemplatesAprovacaoSQLite (US PU-04).

from datetime import datetime, timezone

import pytest

from app.adapters.driven.persistence.repositorio_templates_aprovacao_sqlite import (
    RepositorioTemplatesAprovacaoSQLite,
)
from app.domain.entidades.template_aprovacao import (
    NomePapel,
    TemplateAprovacao,
    TipoFluxo,
)


@pytest.fixture
def caminho_db(tmp_path):
    return str(tmp_path / "templates_test.db")


def _template(projeto="p", tipo="ADR", ativo=True, papeis=(NomePapel.TECH_LEAD,)):
    agora = datetime.now(timezone.utc)
    return TemplateAprovacao(
        projeto_id=projeto,
        tipo_documento=tipo,
        papeis_aprovadores=papeis,
        fluxo=TipoFluxo.SEQUENCIAL,
        ativo=ativo,
        criado_por="alice",
        atualizado_por="alice",
        criado_em=agora,
        atualizado_em=agora,
    )


def test_salvar_e_obter(caminho_db):
    repo = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    t = _template()
    repo.salvar(t)
    encontrado = repo.obter(t.id)
    assert encontrado is not None
    assert encontrado.papeis_aprovadores == (NomePapel.TECH_LEAD,)
    repo.fechar()


def test_persiste_apos_reabrir(caminho_db):
    r1 = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    t = _template()
    r1.salvar(t)
    r1.fechar()

    r2 = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    assert r2.obter(t.id) is not None
    r2.fechar()


def test_listar_filtra_por_projeto_e_ativo(caminho_db):
    repo = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    repo.salvar(_template(projeto="p1", tipo="ADR"))
    repo.salvar(_template(projeto="p1", tipo="RFC", ativo=False))
    repo.salvar(_template(projeto="p2", tipo="ADR"))

    todos = repo.listar()
    assert len(todos) == 3

    so_p1 = repo.listar(projeto_id="p1")
    assert len(so_p1) == 2

    so_ativos = repo.listar(ativo=True)
    assert len(so_ativos) == 2

    so_p1_ativo = repo.listar(projeto_id="p1", ativo=True)
    assert len(so_p1_ativo) == 1
    assert so_p1_ativo[0].tipo_documento == "ADR"
    repo.fechar()


def test_encontrar_ativo_pega_so_ativo(caminho_db):
    repo = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    inativo = _template(ativo=False)
    repo.salvar(inativo)
    assert repo.encontrar_ativo("p", "ADR") is None
    ativo = _template(ativo=True)
    repo.salvar(ativo)
    encontrado = repo.encontrar_ativo("p", "ADR")
    assert encontrado is not None
    assert encontrado.id == ativo.id
    repo.fechar()


def test_remover_devolve_true_no_sucesso(caminho_db):
    repo = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    t = _template()
    repo.salvar(t)
    assert repo.remover(t.id) is True
    assert repo.obter(t.id) is None
    assert repo.remover("nao-existe") is False
    repo.fechar()


def test_upsert_preserva_id(caminho_db):
    repo = RepositorioTemplatesAprovacaoSQLite(caminho_db)
    t = _template(papeis=(NomePapel.TECH_LEAD,))
    repo.salvar(t)
    from dataclasses import replace
    novo = replace(t, papeis_aprovadores=(NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER))
    repo.salvar(novo)
    encontrado = repo.obter(t.id)
    assert encontrado.papeis_aprovadores == (NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER)
    # Garantia: upsert nao criou outro registro.
    assert len(repo.listar()) == 1
    repo.fechar()
