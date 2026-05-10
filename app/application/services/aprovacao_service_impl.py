# Implementacao do AprovacaoService (US PU-05).
# Faz snapshot do template ativo no submeter, processa decisoes respeitando o fluxo
# e gera RegistroAuditoria via PU-06 a cada acao.
# Integracao com PU-07: cada evento dispara notificar_evento(...) para os seguidores.

from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Optional

from app.application.ports.driven.repositorio_aprovacoes import RepositorioAprovacoes
from app.application.ports.driven.repositorio_documentos import RepositorioDocumentos
from app.application.ports.driven.repositorio_templates_aprovacao import (
    RepositorioTemplatesAprovacao,
)
from app.application.ports.driving.aprovacao_service import (
    AprovacaoService,
    StatusDocumento,
)
from app.application.ports.driving.notificacao_service import NotificacaoService
from app.domain.entidades.aprovacao import (
    Aprovacao,
    Decisao,
    DocumentoSubmetido,
    StatusAprovacao,
)
from app.domain.entidades.notificacao import TipoEventoNotificacao
from app.domain.entidades.registro_auditoria import TipoAcao
from app.domain.entidades.template_aprovacao import NomePapel
from app.domain.excecoes import (
    AprovacaoDuplicadaError,
    AprovacaoForaDeOrdemError,
    DocumentoDuplicadoError,
    DocumentoFinalizadoError,
    DocumentoNaoEncontradoError,
    TemplateNaoEncontradoError,
)


_TIPO_RECURSO = "documento_em_aprovacao"


class AprovacaoServiceImpl(AprovacaoService):

    def __init__(
        self,
        repositorio_documentos: RepositorioDocumentos,
        repositorio_aprovacoes: RepositorioAprovacoes,
        repositorio_templates: RepositorioTemplatesAprovacao,
        auditoria,
        notificacao_service: Optional[NotificacaoService] = None,
    ):
        self._docs = repositorio_documentos
        self._decisoes = repositorio_aprovacoes
        self._templates = repositorio_templates
        self._auditoria = auditoria
        self._notificacao = notificacao_service  # opcional — None desliga PU-07

    # ------------------------------------------------------------------
    # Mutacoes
    # ------------------------------------------------------------------

    def submeter(
        self,
        documento_id: str,
        projeto_id: str,
        tipo_documento: str,
        autor_id: str,
        titulo: str,
    ) -> DocumentoSubmetido:
        self._exigir_strings(documento_id=documento_id, projeto_id=projeto_id,
                             tipo_documento=tipo_documento, autor_id=autor_id, titulo=titulo)
        if self._docs.obter(documento_id) is not None:
            raise DocumentoDuplicadoError(f"Documento {documento_id} ja submetido.")

        template = self._templates.encontrar_ativo(projeto_id, tipo_documento)
        if template is None:
            raise TemplateNaoEncontradoError(
                f"Nao ha template ativo para projeto={projeto_id} tipo={tipo_documento}."
            )

        documento = DocumentoSubmetido(
            id=documento_id.strip(),
            projeto_id=projeto_id.strip(),
            tipo_documento=tipo_documento.strip(),
            autor_id=autor_id.strip(),
            titulo=titulo.strip(),
            template_id=template.id,
            papeis_aprovadores=template.papeis_aprovadores,
            fluxo=template.fluxo,
        )
        self._docs.salvar(documento)
        self._auditar(autor_id, TipoAcao.CRIOU, documento, detalhes={
            "titulo": titulo, "template_id": template.id, "fluxo": template.fluxo.value,
        })
        self._notificar(
            documento, TipoEventoNotificacao.DOCUMENTO_SUBMETIDO,
            f"Documento submetido: {titulo}",
            f"O documento {documento.id} foi submetido para aprovacao por {autor_id}.",
            ator=autor_id,
        )
        return documento

    def aprovar(
        self,
        documento_id: str,
        aprovador_id: str,
        papel: NomePapel,
        comentario: str = "",
    ) -> Aprovacao:
        return self._decidir(documento_id, aprovador_id, papel, Decisao.APROVADO, comentario)

    def rejeitar(
        self,
        documento_id: str,
        aprovador_id: str,
        papel: NomePapel,
        comentario: str = "",
    ) -> Aprovacao:
        return self._decidir(documento_id, aprovador_id, papel, Decisao.REJEITADO, comentario)

    def cancelar(
        self,
        documento_id: str,
        autor_id: str,
        motivo: str = "",
    ) -> DocumentoSubmetido:
        self._exigir_strings(documento_id=documento_id, autor_id=autor_id)
        documento = self._exigir_documento(documento_id)
        if documento.status != StatusAprovacao.PENDENTE:
            raise DocumentoFinalizadoError(
                f"Documento ja esta em estado terminal ({documento.status.value})."
            )
        if documento.autor_id != autor_id.strip():
            raise AprovacaoForaDeOrdemError("Apenas o autor pode cancelar a propria submissao.")

        atualizado = replace(
            documento,
            status=StatusAprovacao.CANCELADO,
            finalizado_em=datetime.now(timezone.utc),
            motivo_cancelamento=motivo.strip() or None,
        )
        self._docs.salvar(atualizado)
        self._auditar(autor_id, TipoAcao.EXCLUIU, atualizado, detalhes={"motivo": motivo})
        self._notificar(
            atualizado, TipoEventoNotificacao.DOCUMENTO_CANCELADO,
            f"Documento cancelado: {atualizado.titulo}",
            f"O autor cancelou o documento {atualizado.id}. Motivo: {motivo or 'nao informado'}.",
            ator=autor_id,
        )
        return atualizado

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def consultar(self, documento_id: str) -> StatusDocumento:
        documento = self._exigir_documento(documento_id)
        decisoes = self._decisoes.listar_por_documento(documento_id)
        return StatusDocumento(documento=documento, decisoes=decisoes)

    def fila_pendente(self, papel: NomePapel) -> List[StatusDocumento]:
        pendentes = self._docs.listar(status=StatusAprovacao.PENDENTE)
        out: List[StatusDocumento] = []
        for doc in pendentes:
            decisoes = self._decisoes.listar_por_documento(doc.id)
            if papel in doc.papeis_pendentes(decisoes):
                out.append(StatusDocumento(documento=doc, decisoes=decisoes))
        return out

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _decidir(
        self,
        documento_id: str,
        aprovador_id: str,
        papel: NomePapel,
        decisao: Decisao,
        comentario: str,
    ) -> Aprovacao:
        self._exigir_strings(documento_id=documento_id, aprovador_id=aprovador_id)
        documento = self._exigir_documento(documento_id)
        if documento.status != StatusAprovacao.PENDENTE:
            raise DocumentoFinalizadoError(
                f"Documento ja esta {documento.status.value}; nao aceita mais decisoes."
            )
        if papel not in documento.papeis_aprovadores:
            raise AprovacaoForaDeOrdemError(
                f"Papel '{papel.value}' nao faz parte do template deste documento."
            )

        decisoes_existentes = self._decisoes.listar_por_documento(documento_id)

        if any(d.papel == papel for d in decisoes_existentes):
            raise AprovacaoDuplicadaError(
                f"Papel '{papel.value}' ja decidiu sobre este documento."
            )

        if papel not in documento.papeis_pendentes(decisoes_existentes):
            raise AprovacaoForaDeOrdemError(
                f"Papel '{papel.value}' nao esta pendente agora (fluxo {documento.fluxo.value})."
            )

        aprovacao = Aprovacao(
            documento_id=documento_id.strip(),
            aprovador_id=aprovador_id.strip(),
            papel=papel,
            decisao=decisao,
            comentario=comentario or "",
        )
        self._decisoes.registrar(aprovacao)

        novas_decisoes = decisoes_existentes + [aprovacao]
        novo_status = documento.calcular_status(novas_decisoes)
        documento_apos = documento
        if novo_status != documento.status:
            documento_apos = replace(
                documento,
                status=novo_status,
                finalizado_em=datetime.now(timezone.utc) if novo_status != StatusAprovacao.PENDENTE else None,
            )
            self._docs.salvar(documento_apos)

        acao = TipoAcao.APROVOU if decisao == Decisao.APROVADO else TipoAcao.REJEITOU
        self._auditar(aprovador_id, acao, documento, detalhes={
            "papel": papel.value,
            "comentario": comentario,
            "novo_status": novo_status.value,
        })

        # Notifica seguidores. Se o documento ja chegou ao status terminal, eh evento APROVADO/REJEITADO;
        # caso contrario, mantemos o tipo de acao individual.
        if decisao == Decisao.REJEITADO:
            tipo_evt = TipoEventoNotificacao.DOCUMENTO_REJEITADO
            titulo_msg = f"Documento rejeitado: {documento_apos.titulo}"
        elif novo_status == StatusAprovacao.APROVADO:
            tipo_evt = TipoEventoNotificacao.DOCUMENTO_APROVADO
            titulo_msg = f"Documento aprovado: {documento_apos.titulo}"
        else:
            tipo_evt = TipoEventoNotificacao.OUTRO
            titulo_msg = f"Aprovacao parcial em {documento_apos.titulo}"
        self._notificar(
            documento_apos, tipo_evt, titulo_msg,
            f"{aprovador_id} ({papel.value}) {decisao.value} o documento.",
            ator=aprovador_id,
            extras={"comentario": comentario, "papel": papel.value},
        )
        return aprovacao

    def _exigir_documento(self, documento_id: str) -> DocumentoSubmetido:
        if not documento_id or not documento_id.strip():
            raise DocumentoNaoEncontradoError("documento_id obrigatorio.")
        doc = self._docs.obter(documento_id.strip())
        if doc is None:
            raise DocumentoNaoEncontradoError(f"Documento {documento_id} nao existe.")
        return doc

    @staticmethod
    def _exigir_strings(**campos: str) -> None:
        for nome, valor in campos.items():
            if not valor or not valor.strip():
                from app.domain.excecoes import TemplateInvalidoError  # mantemos a familia
                raise TemplateInvalidoError(f"Campo '{nome}' e obrigatorio.")

    def _auditar(self, usuario_id: str, acao: TipoAcao, documento: DocumentoSubmetido, detalhes: dict) -> None:
        self._auditoria.registrar_acao(
            usuario_id=usuario_id,
            tipo_acao=acao,
            tipo_recurso=_TIPO_RECURSO,
            recurso_id=documento.id,
            detalhes={
                "projeto_id": documento.projeto_id,
                "tipo_documento": documento.tipo_documento,
                **detalhes,
            },
        )

    def _notificar(
        self,
        documento: DocumentoSubmetido,
        tipo: TipoEventoNotificacao,
        titulo: str,
        descricao: str,
        ator: str,
        extras: Optional[dict] = None,
    ) -> None:
        if self._notificacao is None:
            return
        try:
            self._notificacao.notificar_evento(
                documento_id=documento.id,
                tipo=tipo,
                titulo=titulo,
                descricao=descricao,
                detalhes={
                    "projeto_id": documento.projeto_id,
                    "tipo_documento": documento.tipo_documento,
                    "ator": ator,
                    **(extras or {}),
                },
                excluir_usuario=ator,
            )
        except Exception:
            # Notificar nao pode quebrar o fluxo de aprovacao. Logar e seguir.
            import logging
            logging.getLogger("perfis.aprovacao").warning(
                "Falha ao notificar evento %s do documento %s", tipo.value, documento.id,
                exc_info=True,
            )
