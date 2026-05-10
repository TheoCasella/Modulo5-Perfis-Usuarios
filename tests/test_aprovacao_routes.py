# Testes da API HTTP de aprovacao (US PU-05).

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("TEMPLATES_APROVACAO_SQLITE_PATH", str(tmp_path / "templates.db"))
    monkeypatch.setenv("APROVACOES_SQLITE_PATH", str(tmp_path / "aprovacoes.db"))

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _criar_template(cliente, papeis=None, fluxo="sequencial", tipo="ADR"):
    payload = {
        "projeto_id": "p1",
        "tipo_documento": tipo,
        "papeis_aprovadores": papeis or ["tech_lead", "product_manager"],
        "fluxo": fluxo,
        "criado_por": "alice",
    }
    return cliente.post("/api/templates-aprovacao", json=payload).json()


def _submeter(cliente, doc_id="doc-1", tipo="ADR"):
    return cliente.post("/api/documentos/submeter", json={
        "documento_id": doc_id,
        "projeto_id": "p1",
        "tipo_documento": tipo,
        "autor_id": "alice",
        "titulo": f"Doc {doc_id}",
    })


def test_submeter_sem_template_412(cliente):
    r = _submeter(cliente)
    assert r.status_code == 412


def test_submeter_201_e_consultar(cliente):
    _criar_template(cliente)
    r = _submeter(cliente)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pendente"
    assert body["fluxo"] == "sequencial"

    r2 = cliente.get("/api/documentos/doc-1")
    assert r2.status_code == 200
    assert "decisoes" in r2.json()
    assert r2.json()["papeis_pendentes"] == ["tech_lead"]


def test_aprovacoes_sequenciais_finalizam(cliente):
    _criar_template(cliente)
    _submeter(cliente)
    r1 = cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "bob", "papel": "tech_lead", "comentario": "ok",
    })
    assert r1.status_code == 201
    r2 = cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "product_manager", "comentario": "ok",
    })
    assert r2.status_code == 201
    consulta = cliente.get("/api/documentos/doc-1").json()
    assert consulta["status"] == "aprovado"


def test_aprovacao_fora_de_ordem_422(cliente):
    _criar_template(cliente)
    _submeter(cliente)
    r = cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "product_manager",
    })
    assert r.status_code == 422


def test_rejeitar_finaliza_e_proximo_aprovar_409(cliente):
    _criar_template(cliente)
    _submeter(cliente)
    r = cliente.post("/api/documentos/doc-1/rejeitar", json={
        "aprovador_id": "bob", "papel": "tech_lead", "comentario": "nao",
    })
    assert r.status_code == 201
    r2 = cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "product_manager",
    })
    assert r2.status_code == 409


def test_cancelar_so_autor(cliente):
    _criar_template(cliente)
    _submeter(cliente)
    r_outro = cliente.post("/api/documentos/doc-1/cancelar", json={
        "autor_id": "bob", "motivo": "nope",
    })
    assert r_outro.status_code == 403
    r_autor = cliente.post("/api/documentos/doc-1/cancelar", json={
        "autor_id": "alice", "motivo": "obsoleto",
    })
    assert r_autor.status_code == 200
    assert r_autor.json()["status"] == "cancelado"


def test_fila_pendente_por_papel(cliente):
    _criar_template(cliente)
    _submeter(cliente, doc_id="doc-1")
    r = cliente.get("/api/documentos/pendentes/por-papel", params={"papel": "tech_lead"})
    assert r.status_code == 200
    pendentes = r.json()["pendentes"]
    assert len(pendentes) == 1
    assert pendentes[0]["id"] == "doc-1"

    r_pm = cliente.get("/api/documentos/pendentes/por-papel", params={"papel": "product_manager"})
    # SEQUENCIAL: PM nao ve nada ate TL aprovar.
    assert r_pm.json()["pendentes"] == []


def test_audita_fluxo_completo(cliente):
    _criar_template(cliente)
    _submeter(cliente)
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "bob", "papel": "tech_lead",
    })
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "product_manager",
    })
    r = cliente.get("/api/auditoria", params={"tipo_recurso": "documento_em_aprovacao"})
    assert r.status_code == 200
    registros = r.json()["registros"]
    acoes = sorted(r["tipo_acao"] for r in registros)
    assert acoes == ["aprovou", "aprovou", "criou"]
