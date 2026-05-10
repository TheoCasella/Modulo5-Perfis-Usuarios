# Testes do AprovacaoServiceImpl (US PU-05).

from typing import List, Optional

import pytest

from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.application.ports.driven.repositorio_aprovacoes import RepositorioAprovacoes
from app.application.ports.driven.repositorio_documentos import RepositorioDocumentos
from app.application.ports.driven.repositorio_templates_aprovacao import (
    RepositorioTemplatesAprovacao,
)
from app.application.services.aprovacao_service_impl import AprovacaoServiceImpl
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.application.services.template_aprovacao_service_impl import (
    TemplateAprovacaoServiceImpl,
)
from app.domain.entidades.aprovacao import (
    Aprovacao,
    Decisao,
    DocumentoSubmetido,
    StatusAprovacao,
)
from app.domain.entidades.registro_auditoria import FiltroAuditoria, TipoAcao
from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo
from app.domain.excecoes import (
    AprovacaoDuplicadaError,
    AprovacaoForaDeOrdemError,
    DocumentoDuplicadoError,
    DocumentoFinalizadoError,
    DocumentoNaoEncontradoError,
    TemplateNaoEncontradoError,
)


class _RepoTemplatesMemoria(RepositorioTemplatesAprovacao):
    def __init__(self):
        self._dados = {}

    def salvar(self, t):
        self._dados[t.id] = t

    def obter(self, tid):
        return self._dados.get(tid)

    def listar(self, projeto_id=None, ativo=None):
        out = list(self._dados.values())
        if projeto_id:
            out = [t for t in out if t.projeto_id == projeto_id]
        if ativo is not None:
            out = [t for t in out if t.ativo == ativo]
        return out

    def encontrar_ativo(self, projeto_id, tipo_documento):
        for t in self._dados.values():
            if t.projeto_id == projeto_id and t.tipo_documento == tipo_documento and t.ativo:
                return t
        return None

    def remover(self, tid):
        return self._dados.pop(tid, None) is not None


class _RepoDocsMemoria(RepositorioDocumentos):
    def __init__(self):
        self._dados = {}

    def salvar(self, doc):
        self._dados[doc.id] = doc

    def obter(self, did):
        return self._dados.get(did)

    def listar(self, projeto_id=None, status=None):
        out = list(self._dados.values())
        if projeto_id:
            out = [d for d in out if d.projeto_id == projeto_id]
        if status is not None:
            out = [d for d in out if d.status == status]
        return out


class _RepoDecisoesMemoria(RepositorioAprovacoes):
    def __init__(self):
        self._dados: List[Aprovacao] = []

    def registrar(self, a):
        if any(x.id == a.id for x in self._dados):
            raise ValueError("dup")
        self._dados.append(a)

    def listar_por_documento(self, did):
        return sorted(
            [a for a in self._dados if a.documento_id == did],
            key=lambda a: a.decidido_em,
        )


@pytest.fixture
def cenario():
    auditoria = AuditoriaServiceImpl(RepositorioAuditoriaMemoria())
    repo_templates = _RepoTemplatesMemoria()
    template_service = TemplateAprovacaoServiceImpl(repo_templates, auditoria)
    aprovacao_service = AprovacaoServiceImpl(
        repositorio_documentos=_RepoDocsMemoria(),
        repositorio_aprovacoes=_RepoDecisoesMemoria(),
        repositorio_templates=repo_templates,
        auditoria=auditoria,
    )
    return aprovacao_service, template_service, auditoria


def _criar_template(template_service, papeis, fluxo, projeto="proj-1", tipo="ADR"):
    return template_service.criar(projeto, tipo, papeis, fluxo, "alice")


def test_submeter_sem_template_falha(cenario):
    aprovacao_service, _, _ = cenario
    with pytest.raises(TemplateNaoEncontradoError):
        aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Meu doc")


def test_submeter_cria_doc_pendente_e_audita(cenario):
    aprovacao_service, template_service, auditoria = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    doc = aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Meu doc")

    assert doc.status == StatusAprovacao.PENDENTE
    assert doc.papeis_aprovadores == (NomePapel.TECH_LEAD,)
    audits = auditoria.consultar(FiltroAuditoria(tipo_recurso="documento_em_aprovacao"))
    assert len(audits) == 1
    assert audits[0].tipo_acao == TipoAcao.CRIOU


def test_submeter_duplicado_falha(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Meu doc")
    with pytest.raises(DocumentoDuplicadoError):
        aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Outro")


def test_aprovar_papel_fora_do_template_falha(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    with pytest.raises(AprovacaoForaDeOrdemError):
        aprovacao_service.aprovar("doc-1", "bob", NomePapel.PRODUCT_MANAGER)


def test_aprovar_unico_papel_finaliza_doc(cenario):
    aprovacao_service, template_service, auditoria = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD, "lgtm")

    status = aprovacao_service.consultar("doc-1")
    assert status.documento.status == StatusAprovacao.APROVADO
    assert status.documento.finalizado_em is not None
    assert len(status.decisoes) == 1
    assert status.decisoes[0].comentario == "lgtm"

    audits = auditoria.consultar(
        FiltroAuditoria(tipo_recurso="documento_em_aprovacao", tipo_acao=TipoAcao.APROVOU)
    )
    assert len(audits) == 1


def test_rejeitar_finaliza_doc(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.PARALELO,
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.rejeitar("doc-1", "bob", NomePapel.TECH_LEAD, "missing X")

    status = aprovacao_service.consultar("doc-1")
    assert status.documento.status == StatusAprovacao.REJEITADO
    assert status.decisoes[0].decisao == Decisao.REJEITADO


def test_aprovar_apos_finalizado_falha(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    with pytest.raises(DocumentoFinalizadoError):
        aprovacao_service.aprovar("doc-1", "carol", NomePapel.TECH_LEAD)


def test_aprovar_papel_duplicado_falha(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.PARALELO,
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    with pytest.raises(AprovacaoDuplicadaError):
        aprovacao_service.aprovar("doc-1", "carol", NomePapel.TECH_LEAD)


def test_fluxo_sequencial_exige_ordem(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.SEQUENCIAL,
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    # PM antes de TL: erro
    with pytest.raises(AprovacaoForaDeOrdemError):
        aprovacao_service.aprovar("doc-1", "carol", NomePapel.PRODUCT_MANAGER)
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    aprovacao_service.aprovar("doc-1", "carol", NomePapel.PRODUCT_MANAGER)
    assert aprovacao_service.consultar("doc-1").documento.status == StatusAprovacao.APROVADO


def test_fluxo_paralelo_aprova_quando_todos_decidem(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.PARALELO,
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.aprovar("doc-1", "carol", NomePapel.PRODUCT_MANAGER)
    assert aprovacao_service.consultar("doc-1").documento.status == StatusAprovacao.PENDENTE
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    assert aprovacao_service.consultar("doc-1").documento.status == StatusAprovacao.APROVADO


def test_fluxo_qualquer_um_basta_um(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.QUALQUER_UM,
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    assert aprovacao_service.consultar("doc-1").documento.status == StatusAprovacao.APROVADO


def test_cancelar_so_pelo_autor(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(template_service, [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL)
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "Doc")
    with pytest.raises(AprovacaoForaDeOrdemError):
        aprovacao_service.cancelar("doc-1", "bob", "outra pessoa tentando")
    cancelado = aprovacao_service.cancelar("doc-1", "alice", "obsoleto")
    assert cancelado.status == StatusAprovacao.CANCELADO
    assert cancelado.motivo_cancelamento == "obsoleto"


def test_fila_pendente_filtra_por_papel(cenario):
    aprovacao_service, template_service, _ = cenario
    _criar_template(
        template_service,
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.SEQUENCIAL,
        tipo="ADR",
    )
    _criar_template(
        template_service,
        [NomePapel.PRODUCT_MANAGER],
        TipoFluxo.SEQUENCIAL,
        tipo="RFC",
    )
    aprovacao_service.submeter("doc-1", "proj-1", "ADR", "alice", "ADR doc")
    aprovacao_service.submeter("doc-2", "proj-1", "RFC", "alice", "RFC doc")

    fila_tl = aprovacao_service.fila_pendente(NomePapel.TECH_LEAD)
    assert len(fila_tl) == 1
    assert fila_tl[0].documento.id == "doc-1"

    fila_pm = aprovacao_service.fila_pendente(NomePapel.PRODUCT_MANAGER)
    # ADR ainda nao chegou no PM (sequencial); RFC sim.
    assert {s.documento.id for s in fila_pm} == {"doc-2"}

    # Apos TL aprovar o ADR, o PM ve os dois.
    aprovacao_service.aprovar("doc-1", "bob", NomePapel.TECH_LEAD)
    fila_pm_apos = aprovacao_service.fila_pendente(NomePapel.PRODUCT_MANAGER)
    assert {s.documento.id for s in fila_pm_apos} == {"doc-1", "doc-2"}


def test_consultar_documento_inexistente(cenario):
    aprovacao_service, _, _ = cenario
    with pytest.raises(DocumentoNaoEncontradoError):
        aprovacao_service.consultar("nao-existe")
