# Testes do SugestaoOwnershipServiceImpl (US PU-03).

from datetime import datetime, timezone

import pytest

from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.adapters.driven.persistence.repositorio_documentos_sqlite import (
    RepositorioDocumentosSQLite,
)
from app.adapters.driven.persistence.repositorio_ownership_documentos_sqlite import (
    RepositorioOwnershipDocumentosSQLite,
)
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.application.services.sugestao_ownership_service_impl import (
    SugestaoOwnershipServiceImpl,
)
from app.domain.entidades.aprovacao import DocumentoSubmetido, StatusAprovacao
from app.domain.entidades.registro_auditoria import TipoAcao
from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo
from app.domain.excecoes import (
    DocumentoNaoEncontradoError,
    OwnershipJaAtribuidoError,
    SemCandidatoOwnerError,
    SugestaoOwnershipInvalidaError,
)


@pytest.fixture
def cenario(tmp_path):
    repo_docs = RepositorioDocumentosSQLite(str(tmp_path / "docs.db"))
    repo_owners = RepositorioOwnershipDocumentosSQLite(str(tmp_path / "owners.db"))
    auditoria = AuditoriaServiceImpl(RepositorioAuditoriaMemoria())
    service = SugestaoOwnershipServiceImpl(
        repositorio_documentos=repo_docs,
        repositorio_ownership=repo_owners,
        auditoria_service=auditoria,
    )
    yield service, repo_docs, repo_owners, auditoria
    repo_docs.fechar()
    repo_owners.fechar()


def _doc(id="doc-1", projeto="p1", autor="alice", titulo="X"):
    return DocumentoSubmetido(
        id=id, projeto_id=projeto, tipo_documento="ADR",
        autor_id=autor, titulo=titulo, template_id="tmpl-1",
        papeis_aprovadores=(NomePapel.TECH_LEAD,),
        fluxo=TipoFluxo.SEQUENCIAL,
        status=StatusAprovacao.PENDENTE,
    )


# ------------ listar_orfaos ------------

def test_listar_orfaos_sem_atribuicao(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    repo_docs.salvar(_doc(id="d2"))
    orfaos = service.listar_orfaos()
    assert {d.id for d in orfaos} == {"d1", "d2"}


def test_listar_orfaos_filtra_atribuidos(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    repo_docs.salvar(_doc(id="d2"))
    service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="alice")
    orfaos = service.listar_orfaos()
    assert {d.id for d in orfaos} == {"d2"}


def test_listar_orfaos_por_projeto(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1", projeto="p1"))
    repo_docs.salvar(_doc(id="d2", projeto="p2"))
    orfaos = service.listar_orfaos(projeto_id="p1")
    assert {d.id for d in orfaos} == {"d1"}


# ------------ sugerir ------------

def test_sugerir_baseado_em_audit_log(cenario):
    service, repo_docs, _, auditoria = cenario
    repo_docs.salvar(_doc(id="d1", autor="alice"))

    # Bob editou 3x, alice 1x, carol comentou 2x
    for _ in range(3):
        auditoria.registrar_acao("bob", TipoAcao.EDITOU, "documento_em_aprovacao", "d1")
    auditoria.registrar_acao("alice", TipoAcao.CRIOU, "documento_em_aprovacao", "d1")
    for _ in range(2):
        auditoria.registrar_acao("carol", TipoAcao.COMENTOU, "documento_em_aprovacao", "d1")

    sugestao = service.sugerir("d1")
    # Alice criou (peso 5) > bob 3x editou (3*3=9) > carol 2 comentou (2*1=2)
    # Hmm: bob com 9 > alice com 5 > carol com 2
    assert sugestao.candidato_principal.usuario_id == "bob"
    assert sugestao.candidato_principal.score == 9
    # Alternativos contem alice e carol
    alternativos_ids = {c.usuario_id for c in sugestao.candidatos_alternativos}
    assert "alice" in alternativos_ids
    assert "carol" in alternativos_ids


def test_sugerir_fallback_para_autor_quando_sem_audit(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1", autor="alice"))
    sugestao = service.sugerir("d1")
    assert sugestao.candidato_principal.usuario_id == "alice"
    assert "autor original" in sugestao.candidato_principal.motivo


def test_sugerir_documento_inexistente_404(cenario):
    service, _, _, _ = cenario
    with pytest.raises(DocumentoNaoEncontradoError):
        service.sugerir("doc-fantasma")


def test_sugerir_sem_candidato_levanta(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1", autor=""))  # autor vazio + sem audit log
    with pytest.raises(SemCandidatoOwnerError):
        service.sugerir("d1")


def test_sugerir_explicacao_e_motivos(cenario):
    service, repo_docs, _, auditoria = cenario
    repo_docs.salvar(_doc(id="d1", autor="alice"))
    auditoria.registrar_acao("alice", TipoAcao.EDITOU, "documento_em_aprovacao", "d1")
    sugestao = service.sugerir("d1")
    assert "candidato" in sugestao.explicacao.lower()
    assert sugestao.candidato_principal.usuario_id == "alice"
    # motivo identifica que ela eh autor + tem eventos na auditoria
    assert "autor original" in sugestao.candidato_principal.motivo
    assert "evento" in sugestao.candidato_principal.motivo.lower()


# ------------ aprovar_sugestao ------------

def test_aprovar_persiste_e_marca_orfao_resolvido(cenario):
    service, repo_docs, repo_owners, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    ownership = service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="alice", motivo="experiencia")
    assert ownership.owner_id == "alice"
    assert ownership.atribuido_por == "boss"
    persisted = repo_owners.obter("d1")
    assert persisted is not None and persisted.owner_id == "alice"


def test_aprovar_audita_via_pu06(cenario):
    service, repo_docs, _, auditoria = cenario
    repo_docs.salvar(_doc(id="d1"))
    service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="alice")
    from app.domain.entidades.registro_auditoria import FiltroAuditoria
    audits = auditoria.consultar(FiltroAuditoria(tipo_recurso="ownership_documento"))
    assert len(audits) == 1
    assert audits[0].usuario_id == "boss"
    assert audits[0].detalhes.get("owner_id") == "alice"


def test_aprovar_documento_inexistente_404(cenario):
    service, _, _, _ = cenario
    with pytest.raises(DocumentoNaoEncontradoError):
        service.aprovar_sugestao("fantasma", aprovador_id="boss", owner_id="alice")


def test_aprovar_ja_atribuido_409(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="alice")
    with pytest.raises(OwnershipJaAtribuidoError):
        service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="bob")


def test_aprovar_campos_vazios_falha(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    with pytest.raises(SugestaoOwnershipInvalidaError):
        service.aprovar_sugestao("d1", aprovador_id="", owner_id="alice")
    with pytest.raises(SugestaoOwnershipInvalidaError):
        service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="")


# ------------ reatribuir ------------

def test_reatribuir_substitui_owner(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    service.aprovar_sugestao("d1", aprovador_id="boss", owner_id="alice")
    nova = service.reatribuir("d1", aprovador_id="boss", novo_owner_id="bob", motivo="alice saiu")
    assert nova.owner_id == "bob"
    assert nova.fonte.value == "manual"


def test_reatribuir_sem_motivo_falha(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    with pytest.raises(SugestaoOwnershipInvalidaError):
        service.reatribuir("d1", aprovador_id="boss", novo_owner_id="bob", motivo="")


# ------------ obter / listar atribuidos ------------

def test_obter_owner_devolve_none_se_orfao(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    assert service.obter_owner("d1") is None


def test_listar_atribuidos(cenario):
    service, repo_docs, _, _ = cenario
    repo_docs.salvar(_doc(id="d1"))
    repo_docs.salvar(_doc(id="d2"))
    service.aprovar_sugestao("d1", "boss", "alice")
    service.aprovar_sugestao("d2", "boss", "bob")
    atribuidos = service.listar_atribuidos()
    assert {o.documento_id for o in atribuidos} == {"d1", "d2"}
