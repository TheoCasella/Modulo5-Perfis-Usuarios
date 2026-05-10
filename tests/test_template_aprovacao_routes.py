# Testes da API de templates de aprovacao (US PU-04).

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("TEMPLATES_APROVACAO_SQLITE_PATH", str(tmp_path / "templates.db"))

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _payload_basico(**overrides):
    base = {
        "projeto_id": "proj-1",
        "tipo_documento": "ADR",
        "papeis_aprovadores": ["tech_lead", "product_manager"],
        "fluxo": "sequencial",
        "criado_por": "alice",
    }
    base.update(overrides)
    return base


def test_post_cria_template_201(cliente):
    r = cliente.post("/api/templates-aprovacao", json=_payload_basico())
    assert r.status_code == 201
    body = r.json()
    assert body["projeto_id"] == "proj-1"
    assert body["fluxo"] == "sequencial"
    assert body["papeis_aprovadores"] == ["tech_lead", "product_manager"]


def test_post_papel_invalido_400(cliente):
    payload = _payload_basico(papeis_aprovadores=["nao_existe"])
    r = cliente.post("/api/templates-aprovacao", json=payload)
    assert r.status_code == 400


def test_post_duplicado_409(cliente):
    cliente.post("/api/templates-aprovacao", json=_payload_basico())
    r = cliente.post("/api/templates-aprovacao", json=_payload_basico())
    assert r.status_code == 409


def test_get_lista_filtra_por_projeto(cliente):
    cliente.post("/api/templates-aprovacao", json=_payload_basico(projeto_id="p1"))
    cliente.post("/api/templates-aprovacao", json=_payload_basico(projeto_id="p2"))

    r = cliente.get("/api/templates-aprovacao", params={"projeto_id": "p1"})
    assert r.status_code == 200
    assert len(r.json()["templates"]) == 1


def test_get_obter_404_quando_nao_existe(cliente):
    r = cliente.get("/api/templates-aprovacao/nao-existe")
    assert r.status_code == 404


def test_put_atualiza_campos(cliente):
    criado = cliente.post("/api/templates-aprovacao", json=_payload_basico()).json()
    r = cliente.put(
        f"/api/templates-aprovacao/{criado['id']}",
        json={"atualizado_por": "bob", "fluxo": "paralelo"},
    )
    assert r.status_code == 200
    assert r.json()["fluxo"] == "paralelo"


def test_desativar_e_reativar(cliente):
    criado = cliente.post("/api/templates-aprovacao", json=_payload_basico()).json()
    r = cliente.post(
        f"/api/templates-aprovacao/{criado['id']}/desativar",
        json={"atualizado_por": "bob"},
    )
    assert r.status_code == 200
    assert r.json()["ativo"] is False

    r = cliente.post(
        f"/api/templates-aprovacao/{criado['id']}/reativar",
        json={"atualizado_por": "bob"},
    )
    assert r.status_code == 200
    assert r.json()["ativo"] is True


def test_delete_remove_e_devolve_204(cliente):
    criado = cliente.post("/api/templates-aprovacao", json=_payload_basico()).json()
    r = cliente.delete(
        f"/api/templates-aprovacao/{criado['id']}",
        params={"removido_por": "bob"},
    )
    assert r.status_code == 204
    r = cliente.get(f"/api/templates-aprovacao/{criado['id']}")
    assert r.status_code == 404


def test_papeis_pendentes_endpoint(cliente):
    criado = cliente.post(
        "/api/templates-aprovacao",
        json=_payload_basico(papeis_aprovadores=["tech_lead", "product_manager"]),
    ).json()
    r = cliente.get(
        f"/api/templates-aprovacao/{criado['id']}/papeis-pendentes",
        params={"aprovados": ["tech_lead"]},
    )
    assert r.status_code == 200
    assert r.json()["pendentes"] == ["product_manager"]


def test_audita_criacao_via_pu06(cliente):
    cliente.post("/api/templates-aprovacao", json=_payload_basico())
    r = cliente.get("/api/auditoria", params={"tipo_recurso": "template_aprovacao"})
    assert r.status_code == 200
    registros = r.json()["registros"]
    assert len(registros) == 1
    assert registros[0]["tipo_acao"] == "criou"
    assert registros[0]["usuario_id"] == "alice"
