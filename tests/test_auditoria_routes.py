# Testes da API HTTP de auditoria (US PU-06).

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    # Forca backend em memoria + reseta singleton entre testes.
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_post_registrar_201_e_devolve_registro(cliente):
    payload = {
        "usuario_id": "alice",
        "tipo_acao": "visualizou",
        "tipo_recurso": "documento",
        "recurso_id": "doc-1",
        "detalhes": {"ip": "127.0.0.1"},
    }
    r = cliente.post("/api/auditoria/registrar", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["usuario_id"] == "alice"
    assert body["tipo_acao"] == "visualizou"
    assert body["detalhes"] == {"ip": "127.0.0.1"}
    assert "id" in body and "timestamp" in body


def test_post_tipo_acao_invalido_400(cliente):
    payload = {
        "usuario_id": "alice",
        "tipo_acao": "tipo_que_nao_existe",
        "tipo_recurso": "documento",
        "recurso_id": "doc-1",
    }
    r = cliente.post("/api/auditoria/registrar", json=payload)
    assert r.status_code == 400


def test_post_usuario_vazio_400(cliente):
    payload = {
        "usuario_id": "",
        "tipo_acao": "visualizou",
        "tipo_recurso": "documento",
        "recurso_id": "doc-1",
    }
    r = cliente.post("/api/auditoria/registrar", json=payload)
    assert r.status_code == 400


def test_get_consulta_com_filtros(cliente):
    base = {"usuario_id": "alice", "tipo_recurso": "documento", "recurso_id": "doc-1"}
    cliente.post("/api/auditoria/registrar", json={**base, "tipo_acao": "visualizou"})
    cliente.post("/api/auditoria/registrar", json={**base, "tipo_acao": "editou"})
    cliente.post("/api/auditoria/registrar", json={**base, "usuario_id": "bob", "tipo_acao": "visualizou"})

    r = cliente.get("/api/auditoria", params={"usuario_id": "alice"})
    assert r.status_code == 200
    registros = r.json()["registros"]
    assert len(registros) == 2
    assert all(reg["usuario_id"] == "alice" for reg in registros)


def test_get_filtro_por_tipo_acao(cliente):
    base = {"usuario_id": "alice", "tipo_recurso": "documento", "recurso_id": "doc-1"}
    cliente.post("/api/auditoria/registrar", json={**base, "tipo_acao": "visualizou"})
    cliente.post("/api/auditoria/registrar", json={**base, "tipo_acao": "editou"})

    r = cliente.get("/api/auditoria", params={"tipo_acao": "editou"})
    assert r.status_code == 200
    registros = r.json()["registros"]
    assert len(registros) == 1
    assert registros[0]["tipo_acao"] == "editou"


def test_health_ready_endpoint(cliente):
    r = cliente.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["dependencias"]["persistencia_auditoria"] == "ok"


def test_health_liveness(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_nao_expoe_put_delete(cliente):
    r_put = cliente.put("/api/auditoria/algum-id", json={})
    r_delete = cliente.delete("/api/auditoria/algum-id")
    # Imutabilidade: nao deve haver rota — FastAPI devolve 405 (Method Not Allowed) ou 404.
    assert r_put.status_code in (404, 405)
    assert r_delete.status_code in (404, 405)
