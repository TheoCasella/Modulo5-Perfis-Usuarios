# Testes da API HTTP de sugestao de ownership (US PU-03).

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SCHEDULER_HABILITADO", "false")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("TEMPLATES_APROVACAO_SQLITE_PATH", str(tmp_path / "templates.db"))
    monkeypatch.setenv("APROVACOES_SQLITE_PATH", str(tmp_path / "aprovacoes.db"))
    monkeypatch.setenv("NOTIFICACOES_SQLITE_PATH", str(tmp_path / "notif.db"))
    monkeypatch.setenv("OWNERSHIP_DOCUMENTOS_SQLITE_PATH", str(tmp_path / "owners_docs.db"))

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _criar_template(cliente):
    return cliente.post("/api/templates-aprovacao", json={
        "projeto_id": "p1", "tipo_documento": "ADR",
        "papeis_aprovadores": ["tech_lead"], "fluxo": "sequencial",
        "criado_por": "alice",
    }).json()


def _submeter(cliente, doc_id="d1", autor="alice"):
    return cliente.post("/api/documentos/submeter", json={
        "documento_id": doc_id, "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": autor, "titulo": f"Doc {doc_id}",
    })


def test_listar_orfaos_inicial(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    _submeter(cliente, "d2")
    r = cliente.get("/api/sugestao-ownership/orfaos")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2


def test_listar_orfaos_apos_aprovar(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    _submeter(cliente, "d2")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    body = cliente.get("/api/sugestao-ownership/orfaos").json()
    assert body["total"] == 1
    assert body["orfaos"][0]["id"] == "d2"


def test_sugerir_funciona_apos_eventos_de_aprovacao(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1", autor="alice")
    cliente.post("/api/documentos/d1/aprovar", json={
        "aprovador_id": "carol", "papel": "tech_lead",
    })
    r = cliente.get("/api/sugestao-ownership/d1/sugerir")
    assert r.status_code == 200
    body = r.json()
    # alice criou (peso 5) > carol aprovou (peso 2)
    assert body["candidato_principal"]["usuario_id"] == "alice"


def test_sugerir_documento_inexistente_404(cliente):
    r = cliente.get("/api/sugestao-ownership/fantasma/sugerir")
    assert r.status_code == 404


def test_aprovar_201(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    r = cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice", "motivo": "lider tecnico",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["owner_id"] == "alice"
    assert body["fonte"] == "sugestao_aceita"


def test_aprovar_ja_atribuido_409(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    r = cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "bob",
    })
    assert r.status_code == 409


def test_aprovar_documento_inexistente_404(cliente):
    r = cliente.post("/api/sugestao-ownership/fantasma/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    assert r.status_code == 404


def test_aprovar_campos_vazios_400(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    r = cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "", "owner_id": "alice",
    })
    assert r.status_code == 400


def test_reatribuir_substitui(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    r = cliente.post("/api/sugestao-ownership/d1/reatribuir", json={
        "aprovador_id": "boss", "novo_owner_id": "bob", "motivo": "alice saiu da empresa",
    })
    assert r.status_code == 200
    assert r.json()["owner_id"] == "bob"
    assert r.json()["fonte"] == "manual"


def test_reatribuir_sem_motivo_400(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    r = cliente.post("/api/sugestao-ownership/d1/reatribuir", json={
        "aprovador_id": "boss", "novo_owner_id": "bob", "motivo": "",
    })
    assert r.status_code == 400


def test_obter_owner_orfao_404(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    r = cliente.get("/api/sugestao-ownership/d1/owner")
    assert r.status_code == 404


def test_obter_owner_apos_atribuicao(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    r = cliente.get("/api/sugestao-ownership/d1/owner")
    assert r.status_code == 200
    assert r.json()["owner_id"] == "alice"


def test_listar_atribuidos(cliente):
    _criar_template(cliente)
    _submeter(cliente, "d1")
    _submeter(cliente, "d2")
    cliente.post("/api/sugestao-ownership/d1/aprovar", json={
        "aprovador_id": "boss", "owner_id": "alice",
    })
    r = cliente.get("/api/sugestao-ownership/atribuidos")
    assert r.status_code == 200
    assert len(r.json()["atribuidos"]) == 1
