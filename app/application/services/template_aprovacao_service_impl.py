# Implementacao de TemplateAprovacaoService.
# Toda mutacao gera RegistroAuditoria via AuditoriaService (US PU-04 + PU-06).

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.application.ports.driven.repositorio_templates_aprovacao import (
    RepositorioTemplatesAprovacao,
)
from app.application.ports.driving.auditoria_service import AuditoriaService
from app.application.ports.driving.template_aprovacao_service import (
    TemplateAprovacaoService,
)
from app.domain.entidades.registro_auditoria import TipoAcao
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


_TIPO_RECURSO = "template_aprovacao"


class TemplateAprovacaoServiceImpl(TemplateAprovacaoService):

    def __init__(
        self,
        repositorio: RepositorioTemplatesAprovacao,
        auditoria: AuditoriaService,
    ):
        self._repositorio = repositorio
        self._auditoria = auditoria

    # ------------------------------------------------------------------
    # Mutacoes
    # ------------------------------------------------------------------

    def criar(
        self,
        projeto_id: str,
        tipo_documento: str,
        papeis_aprovadores: Iterable[NomePapel],
        fluxo: TipoFluxo,
        criado_por: str,
    ) -> TemplateAprovacao:
        papeis = self._validar_papeis(papeis_aprovadores)
        self._validar_strings(projeto_id=projeto_id, tipo_documento=tipo_documento, criado_por=criado_por)

        existente = self._repositorio.encontrar_ativo(projeto_id, tipo_documento)
        if existente is not None:
            raise TemplateDuplicadoError(
                f"Ja existe template ativo para projeto={projeto_id} tipo={tipo_documento} (id={existente.id})."
            )

        template = TemplateAprovacao(
            projeto_id=projeto_id.strip(),
            tipo_documento=tipo_documento.strip(),
            papeis_aprovadores=papeis,
            fluxo=fluxo,
            criado_por=criado_por.strip(),
            atualizado_por=criado_por.strip(),
        )
        self._repositorio.salvar(template)
        self._auditar(criado_por, TipoAcao.CRIOU, template, mudancas={"criou_template": template.to_dict()})
        return template

    def atualizar(
        self,
        template_id: str,
        atualizado_por: str,
        papeis_aprovadores: Optional[Iterable[NomePapel]] = None,
        fluxo: Optional[TipoFluxo] = None,
        tipo_documento: Optional[str] = None,
    ) -> TemplateAprovacao:
        atual = self._obter_obrigatorio(template_id)
        self._validar_strings(atualizado_por=atualizado_por)

        mudancas: Dict[str, Any] = {}
        novos_papeis = atual.papeis_aprovadores
        if papeis_aprovadores is not None:
            novos_papeis = self._validar_papeis(papeis_aprovadores)
            if novos_papeis != atual.papeis_aprovadores:
                mudancas["papeis_aprovadores"] = {
                    "antes": [p.value for p in atual.papeis_aprovadores],
                    "depois": [p.value for p in novos_papeis],
                }

        novo_fluxo = atual.fluxo
        if fluxo is not None and fluxo != atual.fluxo:
            novo_fluxo = fluxo
            mudancas["fluxo"] = {"antes": atual.fluxo.value, "depois": fluxo.value}

        novo_tipo = atual.tipo_documento
        if tipo_documento is not None and tipo_documento.strip() != atual.tipo_documento:
            novo_tipo = tipo_documento.strip()
            mudancas["tipo_documento"] = {"antes": atual.tipo_documento, "depois": novo_tipo}

        if not mudancas:
            return atual

        atualizado = replace(
            atual,
            papeis_aprovadores=novos_papeis,
            fluxo=novo_fluxo,
            tipo_documento=novo_tipo,
            atualizado_por=atualizado_por.strip(),
            atualizado_em=datetime.now(timezone.utc),
        )
        self._repositorio.salvar(atualizado)
        self._auditar(atualizado_por, TipoAcao.EDITOU, atualizado, mudancas=mudancas)
        return atualizado

    def desativar(self, template_id: str, atualizado_por: str) -> TemplateAprovacao:
        atual = self._obter_obrigatorio(template_id)
        if not atual.ativo:
            return atual
        self._validar_strings(atualizado_por=atualizado_por)
        atualizado = replace(
            atual,
            ativo=False,
            atualizado_por=atualizado_por.strip(),
            atualizado_em=datetime.now(timezone.utc),
        )
        self._repositorio.salvar(atualizado)
        self._auditar(atualizado_por, TipoAcao.EDITOU, atualizado, mudancas={"ativo": {"antes": True, "depois": False}})
        return atualizado

    def reativar(self, template_id: str, atualizado_por: str) -> TemplateAprovacao:
        atual = self._obter_obrigatorio(template_id)
        if atual.ativo:
            return atual
        self._validar_strings(atualizado_por=atualizado_por)
        # Antes de reativar, garantir que nao ha outro ativo concorrente.
        concorrente = self._repositorio.encontrar_ativo(atual.projeto_id, atual.tipo_documento)
        if concorrente is not None and concorrente.id != atual.id:
            raise TemplateDuplicadoError(
                f"Existe outro template ativo para o mesmo projeto+tipo (id={concorrente.id}). "
                f"Desative-o antes de reativar este."
            )
        atualizado = replace(
            atual,
            ativo=True,
            atualizado_por=atualizado_por.strip(),
            atualizado_em=datetime.now(timezone.utc),
        )
        self._repositorio.salvar(atualizado)
        self._auditar(atualizado_por, TipoAcao.EDITOU, atualizado, mudancas={"ativo": {"antes": False, "depois": True}})
        return atualizado

    def remover(self, template_id: str, removido_por: str) -> None:
        atual = self._obter_obrigatorio(template_id)
        self._validar_strings(removido_por=removido_por)
        ok = self._repositorio.remover(template_id)
        if not ok:
            raise TemplateNaoEncontradoError(f"Template {template_id} nao foi removido.")
        self._auditar(removido_por, TipoAcao.EXCLUIU, atual, mudancas={"removeu_template": atual.to_dict()})

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obter(self, template_id: str) -> TemplateAprovacao:
        return self._obter_obrigatorio(template_id)

    def listar(
        self,
        projeto_id: Optional[str] = None,
        ativo: Optional[bool] = None,
    ) -> List[TemplateAprovacao]:
        return self._repositorio.listar(projeto_id=projeto_id, ativo=ativo)

    def papeis_pendentes(
        self,
        template_id: str,
        papeis_ja_aprovaram: Iterable[NomePapel],
    ) -> List[NomePapel]:
        template = self._obter_obrigatorio(template_id)
        ja_aprovaram = set(papeis_ja_aprovaram)

        if template.fluxo == TipoFluxo.PARALELO:
            return [p for p in template.papeis_aprovadores if p not in ja_aprovaram]

        if template.fluxo == TipoFluxo.QUALQUER_UM:
            # Se alguem ja aprovou, ninguem mais precisa.
            if ja_aprovaram & set(template.papeis_aprovadores):
                return []
            return list(template.papeis_aprovadores)

        # SEQUENCIAL: o proximo eh o primeiro papel da fila que ainda nao aprovou.
        for papel in template.papeis_aprovadores:
            if papel not in ja_aprovaram:
                return [papel]
        return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _obter_obrigatorio(self, template_id: str) -> TemplateAprovacao:
        if not template_id or not template_id.strip():
            raise TemplateInvalidoError("template_id e obrigatorio.")
        encontrado = self._repositorio.obter(template_id.strip())
        if encontrado is None:
            raise TemplateNaoEncontradoError(f"Template {template_id} nao existe.")
        return encontrado

    @staticmethod
    def _validar_papeis(papeis: Iterable[NomePapel]) -> tuple:
        lista = tuple(papeis)
        if not lista:
            raise TemplateInvalidoError("Lista de papeis aprovadores nao pode ser vazia.")
        # Sem duplicatas — a ordem importa em fluxo SEQUENCIAL, mas duplicar nao faz sentido.
        if len(set(lista)) != len(lista):
            raise TemplateInvalidoError("Papeis aprovadores duplicados nao sao permitidos.")
        return lista

    @staticmethod
    def _validar_strings(**campos: str) -> None:
        for nome, valor in campos.items():
            if not valor or not valor.strip():
                raise TemplateInvalidoError(f"Campo '{nome}' e obrigatorio.")

    def _auditar(
        self,
        usuario_id: str,
        acao: TipoAcao,
        template: TemplateAprovacao,
        mudancas: Dict[str, Any],
    ) -> None:
        self._auditoria.registrar_acao(
            usuario_id=usuario_id,
            tipo_acao=acao,
            tipo_recurso=_TIPO_RECURSO,
            recurso_id=template.id,
            detalhes={
                "projeto_id": template.projeto_id,
                "tipo_documento": template.tipo_documento,
                **mudancas,
            },
        )
