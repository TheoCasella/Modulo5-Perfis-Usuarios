# Testes das rotas REST de ownership (US PU-09).

import importlib

import pytest

from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError


@pytest.fixture
def cliente_e_root(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("OWNERSHIP_CACHE_TTL_SEGUNDOS", "3600")

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


def test_get_ownership_com_dados_no_fake_devolve_github_vivo(cliente_e_root):
    cliente, root = cliente_e_root
    root.provedor_historico.configurar(
        "fnavai/Modulo5-Interface-e-Nuvem",
        "app/main.py",
        Ownership(
            repositorio="fnavai/Modulo5-Interface-e-Nuvem",
            modulo="app/main.py",
            owner_id="fnavai",
            confianca=0.9,
            total_commits=20,
        ),
    )
    r = cliente.get(
        "/api/ownership",
        params={"repositorio": "fnavai/Modulo5-Interface-e-Nuvem", "modulo": "app/main.py"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["origem"] == "github_vivo"
    assert body["ownership"]["owner_id"] == "fnavai"
    assert body["aviso"] is None


def test_github_fora_sem_cache_devolve_503_amigavel(cliente_e_root):
    cliente, root = cliente_e_root
    root.provedor_historico.fazer_falhar_com(GitHubIndisponivelError("rate limit"))

    r = cliente.get("/api/ownership", params={"repositorio": "x/y", "modulo": "z.py"})
    assert r.status_code == 503
    detalhe = r.json()["detail"]
    assert "tente" in detalhe["mensagem"].lower()


def test_github_fora_com_cache_devolve_200_fallback(cliente_e_root):
    cliente, root = cliente_e_root
    root.repositorio_ownership.salvar(Ownership(
        repositorio="x/y",
        modulo="z.py",
        owner_id="alice",
        confianca=0.7,
        total_commits=5,
    ))
    root.provedor_historico.fazer_falhar_com(GitHubIndisponivelError("502"))

    # Muda o TTL pra 0 pra forcar consulta ao "github" (que ta falhando) — assim cai no cache
    from app.application.services.ownership_service_impl import OwnershipServiceImpl
    root.ownership_service = OwnershipServiceImpl(
        provedor_historico=root.provedor_historico,
        repositorio=root.repositorio_ownership,
        cache_ttl_segundos=0,
    )

    r = cliente.get("/api/ownership", params={"repositorio": "x/y", "modulo": "z.py"})
    assert r.status_code == 200
    body = r.json()
    assert body["origem"] == "fallback_cache"
    assert body["ownership"]["owner_id"] == "alice"
    assert body["aviso"] is not None


def test_listar_conhecidos_so_le_cache(cliente_e_root):
    cliente, root = cliente_e_root
    root.repositorio_ownership.salvar(Ownership(
        repositorio="x/y", modulo="a", owner_id="alice", confianca=0.5, total_commits=2,
    ))
    root.repositorio_ownership.salvar(Ownership(
        repositorio="x/y", modulo="b", owner_id="bob", confianca=0.6, total_commits=3,
    ))
    # GitHub fora de proposito — listar nao deve falhar
    root.provedor_historico.fazer_falhar_com(GitHubIndisponivelError("vai cair se chamado"))

    r = cliente.get("/api/ownership/conhecidos", params={"repositorio": "x/y"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["ownerships"]) == 2
    assert {o["owner_id"] for o in body["ownerships"]} == {"alice", "bob"}
