# Testes da API HTTP de notificacoes (US PU-07).
# Tambem cobre a integracao com PU-05: aprovar/rejeitar gera notificacao para seguidores.

import importlib

import pytest


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITORIA_BACKEND", "memoria")
    monkeypatch.setenv("PROVEDOR_HISTORICO_COMMITS", "fake")
    monkeypatch.setenv("OWNERSHIP_SQLITE_PATH", str(tmp_path / "ownership.db"))
    monkeypatch.setenv("TEMPLATES_APROVACAO_SQLITE_PATH", str(tmp_path / "templates.db"))
    monkeypatch.setenv("APROVACOES_SQLITE_PATH", str(tmp_path / "aprovacoes.db"))
    monkeypatch.setenv("NOTIFICACOES_SQLITE_PATH", str(tmp_path / "notif.db"))

    from app.config import composition_root, settings
    importlib.reload(settings)
    importlib.reload(composition_root)
    composition_root._singleton = None

    from fastapi.testclient import TestClient
    import main as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _seguir(cliente, usuario, documento):
    return cliente.post("/api/notificacoes/seguir", json={
        "usuario_id": usuario, "documento_id": documento,
    })


def test_seguir_201(cliente):
    r = _seguir(cliente, "alice", "doc-1")
    assert r.status_code == 201
    assert r.json()["usuario_id"] == "alice"


def test_seguir_duplicado_409(cliente):
    _seguir(cliente, "alice", "doc-1")
    r = _seguir(cliente, "alice", "doc-1")
    assert r.status_code == 409


def test_seguir_campos_vazios_400(cliente):
    r = _seguir(cliente, "", "doc-1")
    assert r.status_code == 400


def test_parar_de_seguir_204_e_404(cliente):
    _seguir(cliente, "alice", "doc-1")
    r = cliente.delete("/api/notificacoes/seguir/doc-1?usuario_id=alice")
    assert r.status_code == 204
    r = cliente.delete("/api/notificacoes/seguir/doc-1?usuario_id=alice")
    assert r.status_code == 404


def test_listar_seguidores_e_seguidos(cliente):
    _seguir(cliente, "alice", "doc-1")
    _seguir(cliente, "bob", "doc-1")
    r = cliente.get("/api/notificacoes/seguidores/doc-1")
    assert r.status_code == 200
    assert set(r.json()["seguidores"]) == {"alice", "bob"}

    r = cliente.get("/api/notificacoes/seguidos?usuario_id=alice")
    assert r.status_code == 200
    assert {s["documento_id"] for s in r.json()["seguidos"]} == {"doc-1"}


def _criar_template(cliente, papeis=("tech_lead",), tipo="ADR"):
    return cliente.post("/api/templates-aprovacao", json={
        "projeto_id": "p1", "tipo_documento": tipo,
        "papeis_aprovadores": list(papeis), "fluxo": "sequencial",
        "criado_por": "alice",
    }).json()


def test_aprovacao_gera_notificacao_para_seguidores(cliente):
    _criar_template(cliente)
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Meu doc",
    })
    # bob segue o documento
    _seguir(cliente, "bob", "doc-1")
    # tech_lead aprova
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "tech_lead", "comentario": "lgtm",
    })

    # bob deve ter recebido notificacao
    r = cliente.get("/api/notificacoes?usuario_id=bob")
    assert r.status_code == 200
    notificacoes = r.json()["notificacoes"]
    assert len(notificacoes) == 1
    assert notificacoes[0]["tipo_evento"] == "documento_aprovado"
    assert "Meu doc" in notificacoes[0]["titulo"]


def test_submissao_notifica_seguidores_pre_existentes(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    r = cliente.get("/api/notificacoes?usuario_id=bob")
    notif = r.json()["notificacoes"]
    assert len(notif) == 1
    assert notif[0]["tipo_evento"] == "documento_submetido"


def test_ator_nao_se_notifica(cliente):
    _criar_template(cliente)
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    # alice segue ela mesma o documento (cenario raro mas possivel)
    _seguir(cliente, "alice", "doc-1")
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "alice", "papel": "tech_lead",
    })
    r = cliente.get("/api/notificacoes?usuario_id=alice")
    # alice eh a aprovadora — nao deve receber notificacao
    assert r.json()["notificacoes"] == []


def test_marcar_como_lida(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    notif = cliente.get("/api/notificacoes?usuario_id=bob").json()["notificacoes"][0]
    assert notif["lida"] is False
    r = cliente.post(f"/api/notificacoes/{notif['id']}/marcar-lida", json={"usuario_id": "bob"})
    assert r.status_code == 200
    assert r.json()["lida"] is True


def test_marcar_lida_de_outro_usuario_404(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    notif = cliente.get("/api/notificacoes?usuario_id=bob").json()["notificacoes"][0]
    r = cliente.post(f"/api/notificacoes/{notif['id']}/marcar-lida", json={"usuario_id": "carol"})
    assert r.status_code == 404


def test_contagem_nao_lidas(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "tech_lead",
    })
    r = cliente.get("/api/notificacoes/contagem-nao-lidas?usuario_id=bob")
    assert r.status_code == 200
    assert r.json()["nao_lidas"] == 2


def test_marcar_todas_lidas(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "tech_lead",
    })
    r = cliente.post("/api/notificacoes/marcar-todas-lidas", json={"usuario_id": "bob"})
    assert r.json()["marcadas"] == 2
    assert cliente.get("/api/notificacoes/contagem-nao-lidas?usuario_id=bob").json()["nao_lidas"] == 0


def test_filtros_lida_e_documento(cliente):
    _criar_template(cliente)
    _seguir(cliente, "bob", "doc-1")
    cliente.post("/api/documentos/submeter", json={
        "documento_id": "doc-1", "projeto_id": "p1", "tipo_documento": "ADR",
        "autor_id": "alice", "titulo": "Doc",
    })
    cliente.post("/api/documentos/doc-1/aprovar", json={
        "aprovador_id": "carol", "papel": "tech_lead",
    })

    nao_lidas = cliente.get("/api/notificacoes?usuario_id=bob&lida=false").json()["notificacoes"]
    assert len(nao_lidas) == 2

    so_doc1 = cliente.get("/api/notificacoes?usuario_id=bob&documento_id=doc-1").json()["notificacoes"]
    assert len(so_doc1) == 2
