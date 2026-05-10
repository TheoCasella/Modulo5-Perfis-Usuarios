# Testes do TemplateAprovacaoServiceImpl (US PU-04).

from typing import List, Optional

import pytest

from app.adapters.driven.persistence.repositorio_auditoria_memoria import (
    RepositorioAuditoriaMemoria,
)
from app.application.ports.driven.repositorio_templates_aprovacao import (
    RepositorioTemplatesAprovacao,
)
from app.application.services.auditoria_service_impl import AuditoriaServiceImpl
from app.application.services.template_aprovacao_service_impl import (
    TemplateAprovacaoServiceImpl,
)
from app.domain.entidades.registro_auditoria import FiltroAuditoria, TipoAcao
from app.domain.entidades.template_aprovacao import (
    NomePapel,
    TemplateAprovacao,
    TipoFluxo,
)
from app.domain.excecoes import (
    TemplateDuplicadoError,
    TemplateInvalidoError,
    TemplateNaoEncontradoError,
)


class _RepoMemoria(RepositorioTemplatesAprovacao):
    def __init__(self):
        self._dados = {}

    def salvar(self, template):
        self._dados[template.id] = template

    def obter(self, template_id):
        return self._dados.get(template_id)

    def listar(self, projeto_id=None, ativo=None):
        out = list(self._dados.values())
        if projeto_id is not None:
            out = [t for t in out if t.projeto_id == projeto_id]
        if ativo is not None:
            out = [t for t in out if t.ativo == ativo]
        return out

    def encontrar_ativo(self, projeto_id, tipo_documento):
        for t in self._dados.values():
            if t.projeto_id == projeto_id and t.tipo_documento == tipo_documento and t.ativo:
                return t
        return None

    def remover(self, template_id):
        return self._dados.pop(template_id, None) is not None


@pytest.fixture
def service_e_auditoria():
    auditoria_repo = RepositorioAuditoriaMemoria()
    auditoria = AuditoriaServiceImpl(auditoria_repo)
    template_repo = _RepoMemoria()
    service = TemplateAprovacaoServiceImpl(template_repo, auditoria)
    return service, auditoria, template_repo


def test_criar_template_persiste_e_audita(service_e_auditoria):
    service, auditoria, repo = service_e_auditoria
    t = service.criar(
        projeto_id="proj-1",
        tipo_documento="ADR",
        papeis_aprovadores=[NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        fluxo=TipoFluxo.SEQUENCIAL,
        criado_por="alice",
    )
    assert repo.obter(t.id) is not None
    audits = auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao"))
    assert len(audits) == 1
    assert audits[0].tipo_acao == TipoAcao.CRIOU
    assert audits[0].usuario_id == "alice"


def test_criar_duplicado_falha(service_e_auditoria):
    service, _, _ = service_e_auditoria
    service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.PARALELO, "alice")
    with pytest.raises(TemplateDuplicadoError):
        service.criar("p", "ADR", [NomePapel.PRODUCT_MANAGER], TipoFluxo.PARALELO, "bob")


def test_criar_papeis_vazios_falha(service_e_auditoria):
    service, _, _ = service_e_auditoria
    with pytest.raises(TemplateInvalidoError):
        service.criar("p", "ADR", [], TipoFluxo.SEQUENCIAL, "alice")


def test_criar_papeis_duplicados_falha(service_e_auditoria):
    service, _, _ = service_e_auditoria
    with pytest.raises(TemplateInvalidoError):
        service.criar(
            "p", "ADR",
            [NomePapel.TECH_LEAD, NomePapel.TECH_LEAD],
            TipoFluxo.SEQUENCIAL,
            "alice",
        )


def test_atualizar_audita_so_diff(service_e_auditoria):
    service, auditoria, _ = service_e_auditoria
    t = service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL, "alice")
    audits_iniciais = auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao"))

    novo = service.atualizar(t.id, "bob", fluxo=TipoFluxo.PARALELO)
    assert novo.fluxo == TipoFluxo.PARALELO
    assert novo.atualizado_por == "bob"

    audits_edicao = auditoria.consultar(
        FiltroAuditoria(tipo_recurso="template_aprovacao", tipo_acao=TipoAcao.EDITOU)
    )
    assert len(audits_edicao) == 1
    assert audits_edicao[0].usuario_id == "bob"
    # Total = inicial (CRIOU) + 1 (EDITOU)
    todos = auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao"))
    assert len(todos) == len(audits_iniciais) + 1


def test_atualizar_sem_mudancas_nao_audita(service_e_auditoria):
    service, auditoria, _ = service_e_auditoria
    t = service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL, "alice")
    audits_iniciais = len(auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao")))
    service.atualizar(t.id, "bob")  # nada muda
    audits_pos = auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao"))
    assert len(audits_pos) == audits_iniciais


def test_desativar_e_reativar(service_e_auditoria):
    service, _, _ = service_e_auditoria
    t = service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL, "alice")
    desativado = service.desativar(t.id, "bob")
    assert desativado.ativo is False
    reativado = service.reativar(desativado.id, "bob")
    assert reativado.ativo is True


def test_reativar_com_outro_ativo_falha(service_e_auditoria):
    service, _, _ = service_e_auditoria
    t1 = service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL, "alice")
    service.desativar(t1.id, "alice")
    service.criar("p", "ADR", [NomePapel.PRODUCT_MANAGER], TipoFluxo.SEQUENCIAL, "alice")
    with pytest.raises(TemplateDuplicadoError):
        service.reativar(t1.id, "alice")


def test_remover_audita_e_some(service_e_auditoria):
    service, auditoria, repo = service_e_auditoria
    t = service.criar("p", "ADR", [NomePapel.TECH_LEAD], TipoFluxo.SEQUENCIAL, "alice")
    service.remover(t.id, "bob")
    assert repo.obter(t.id) is None
    audits = auditoria.consultar(FiltroAuditoria(tipo_recurso="template_aprovacao", tipo_acao=TipoAcao.EXCLUIU))
    assert len(audits) == 1


def test_obter_inexistente_levanta(service_e_auditoria):
    service, _, _ = service_e_auditoria
    with pytest.raises(TemplateNaoEncontradoError):
        service.obter("nao-existe")


def test_papeis_pendentes_sequencial(service_e_auditoria):
    service, _, _ = service_e_auditoria
    t = service.criar(
        "p", "ADR",
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER, NomePapel.GERENTE],
        TipoFluxo.SEQUENCIAL,
        "alice",
    )
    # Ninguem aprovou: o primeiro pendente eh o tech lead.
    assert service.papeis_pendentes(t.id, []) == [NomePapel.TECH_LEAD]
    # TL aprovou: PM eh o proximo (ainda 1 da fila).
    assert service.papeis_pendentes(t.id, [NomePapel.TECH_LEAD]) == [NomePapel.PRODUCT_MANAGER]
    # Todos aprovaram: lista vazia.
    assert service.papeis_pendentes(
        t.id, [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER, NomePapel.GERENTE]
    ) == []


def test_papeis_pendentes_paralelo(service_e_auditoria):
    service, _, _ = service_e_auditoria
    t = service.criar(
        "p", "ADR",
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.PARALELO,
        "alice",
    )
    pendentes = service.papeis_pendentes(t.id, [NomePapel.TECH_LEAD])
    assert pendentes == [NomePapel.PRODUCT_MANAGER]


def test_papeis_pendentes_qualquer_um(service_e_auditoria):
    service, _, _ = service_e_auditoria
    t = service.criar(
        "p", "ADR",
        [NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER],
        TipoFluxo.QUALQUER_UM,
        "alice",
    )
    # Sem nenhuma aprovacao: qualquer um pode aprovar.
    assert set(service.papeis_pendentes(t.id, [])) == {NomePapel.TECH_LEAD, NomePapel.PRODUCT_MANAGER}
    # Basta um aprovar pra zerar pendentes.
    assert service.papeis_pendentes(t.id, [NomePapel.TECH_LEAD]) == []
