# Testes dos novos endpoints REST de PU-02.

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("OWNERSHIP_CACHE_TTL_SEGUNDOS", "3600")
    monkeypatch.setenv("OWNERSHIP_SCHEDULER_HABILITADO", "false")  # nao iniciamos thread em testes
    monkeypatch.setenv("NOTIFICACOES_SQLITE_PATH", str(tmp_path / "notif.db"))

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    cliente = TestClient(app_module.app)
    root = composition_root.get_root()
    return cliente, root


def test_registrar_modulos_201(cliente):
    cli, root = cliente
    from app.domain.entidades.ownership import Ownership
    root.provedor_historico.configurar("o/r", "a.py", Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.9, total_commits=10,
    ))
    r = cli.post("/api/ownership/registrar", json={
        "repositorio": "o/r", "modulos": ["a.py", "b.py"],
    })
    assert r.status_code == 201
    body = r.json()
    assert body["total"] == 2
    # a.py: alice (consulta deu certo); b.py: placeholder (sem dado configurado)
    owners = {item["owner_id"] for item in body["registrados"]}
    assert "alice" in owners
    assert "(desconhecido)" in owners


def test_registrar_modulos_payload_invalido_400(cliente):
    cli, _ = cliente
    r = cli.post("/api/ownership/registrar", json={"repositorio": "", "modulos": []})
    assert r.status_code == 400


def test_refrescar_devolve_resumo(cliente):
    cli, root = cliente
    from app.domain.entidades.ownership import Ownership
    root.repositorio_ownership.salvar(Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.6, total_commits=3,
    ))
    root.provedor_historico.configurar("o/r", "a.py", Ownership(
        repositorio="o/r", modulo="a.py", owner_id="bob", confianca=0.9, total_commits=10,
    ))
    r = cli.post("/api/ownership/refrescar")
    assert r.status_code == 200
    body = r.json()
    assert body["total_avaliados"] == 1
    assert body["refrescados"] == 1
    assert body["falhas"] == 0
    assert "duracao_segundos" in body


def test_refrescar_sem_dados_devolve_zero(cliente):
    cli, _ = cliente
    r = cli.post("/api/ownership/refrescar")
    assert r.status_code == 200
    body = r.json()
    assert body["total_avaliados"] == 0
