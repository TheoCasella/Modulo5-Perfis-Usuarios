# Testes dos repositorios SQLite de aprovacao (US PU-05).

from datetime import datetime, timezone

import pytest

from app.adapters.driven.persistence.repositorio_aprovacoes_sqlite import (
    RepositorioAprovacoesSQLite,
)
from app.adapters.driven.persistence.repositorio_documentos_sqlite import (
    RepositorioDocumentosSQLite,
)
from app.domain.entidades.aprovacao import (
    Aprovacao,
    Decisao,
    DocumentoSubmetido,
    StatusAprovacao,
)
from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo


@pytest.fixture
def caminho_db(tmp_path):
    return str(tmp_path / "aprovacoes.db")


def _doc(id="doc-1", status=StatusAprovacao.PENDENTE):
    agora = datetime.now(timezone.utc)
    return DocumentoSubmetido(
        id=id,
        projeto_id="p1",
        tipo_documento="ADR",
        autor_id="alice",
        titulo="Doc",
        template_id="tmpl-1",
        papeis_aprovadores=(NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER),
        fluxo=TipoFluxo.SEQUENCIAL,
        status=status,
        submetido_em=agora,
    )


def test_doc_round_trip(caminho_db):
    repo = RepositorioDocumentosSQLite(caminho_db)
    repo.salvar(_doc())
    encontrado = repo.obter("doc-1")
    assert encontrado is not None
    assert encontrado.papeis_aprovadores == (NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER)
    assert encontrado.fluxo == TipoFluxo.SEQUENCIAL
    repo.fechar()


def test_doc_upsert_atualiza_status(caminho_db):
    repo = RepositorioDocumentosSQLite(caminho_db)
    repo.salvar(_doc())
    from dataclasses import replace
    repo.salvar(replace(_doc(), status=StatusAprovacao.APROVADO))
    encontrado = repo.obter("doc-1")
    assert encontrado.status == StatusAprovacao.APROVADO
    repo.fechar()


def test_doc_listar_filtra_por_status(caminho_db):
    repo = RepositorioDocumentosSQLite(caminho_db)
    repo.salvar(_doc(id="d1", status=StatusAprovacao.PENDENTE))
    repo.salvar(_doc(id="d2", status=StatusAprovacao.APROVADO))
    pendentes = repo.listar(status=StatusAprovacao.PENDENTE)
    assert {d.id for d in pendentes} == {"d1"}
    repo.fechar()


def test_aprovacoes_round_trip(caminho_db):
    repo = RepositorioAprovacoesSQLite(caminho_db)
    a = Aprovacao(
        documento_id="doc-1",
        aprovador_id="bob",
        papel=NomePapel.TECH_LEAD,
        decisao=Decisao.APROVADO,
        comentario="lgtm",
    )
    repo.registrar(a)
    encontrados = repo.listar_por_documento("doc-1")
    assert len(encontrados) == 1
    assert encontrados[0].aprovador_id == "bob"
    assert encontrados[0].papel == NomePapel.TECH_LEAD
    repo.fechar()


def test_aprovacoes_id_duplicado_falha(caminho_db):
    repo = RepositorioAprovacoesSQLite(caminho_db)
    a = Aprovacao(
        documento_id="d", aprovador_id="b", papel=NomePapel.TECH_LEAD, decisao=Decisao.APROVADO,
    )
    repo.registrar(a)
    with pytest.raises(ValueError):
        repo.registrar(a)
    repo.fechar()


def test_persiste_apos_reabrir(caminho_db):
    r1 = RepositorioDocumentosSQLite(caminho_db)
    r1.salvar(_doc())
    r1.fechar()
    r2 = RepositorioDocumentosSQLite(caminho_db)
    assert r2.obter("doc-1") is not None
    r2.fechar()
