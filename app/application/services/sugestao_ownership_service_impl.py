# Implementacao do SugestaoOwnershipService (US PU-03).
# Cruza PU-05 (RepositorioDocumentos), PU-06 (AuditoriaService) e o repo proprio.

from collections import Counter
from typing import List, Optional

from app.application.ports.driven.repositorio_documentos import RepositorioDocumentos
from app.application.ports.driven.repositorio_ownership_documentos import (
    RepositorioOwnershipDocumentos,
)
from app.application.ports.driving.auditoria_service import AuditoriaService
from app.application.ports.driving.sugestao_ownership_service import (
    SugestaoOwnershipService,
)
from app.domain.entidades.aprovacao import DocumentoSubmetido
from app.domain.entidades.ownership_documento import (
    CandidatoOwner,
    FonteOwnership,
    OwnershipDocumento,
    SugestaoOwnership,
)
from app.domain.entidades.registro_auditoria import FiltroAuditoria, TipoAcao
from app.domain.excecoes import (
    DocumentoNaoEncontradoError,
    OwnershipJaAtribuidoError,
    SemCandidatoOwnerError,
    SugestaoOwnershipInvalidaError,
)


# Pesos das acoes para pontuar candidatos.
# Criar > Editar > Aprovar > Comentar — refletindo grau de "investimento" no documento.
_PESOS_ACAO = {
    TipoAcao.CRIOU: 5,
    TipoAcao.EDITOU: 3,
    TipoAcao.APROVOU: 2,
    TipoAcao.REJEITOU: 1,
    TipoAcao.COMENTOU: 1,
}

_TIPOS_RECURSO_DOC = ("documento_em_aprovacao", "documento")


class SugestaoOwnershipServiceImpl(SugestaoOwnershipService):

    def __init__(
        self,
        repositorio_documentos: RepositorioDocumentos,
        repositorio_ownership: RepositorioOwnershipDocumentos,
        auditoria_service: AuditoriaService,
    ):
        self._docs = repositorio_documentos
        self._owners = repositorio_ownership
        self._auditoria = auditoria_service

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar_orfaos(self, projeto_id: Optional[str] = None) -> List[DocumentoSubmetido]:
        todos = self._docs.listar(projeto_id=projeto_id)
        com_owner = self._owners.documentos_com_owner()
        return [d for d in todos if d.id not in com_owner]

    def sugerir(self, documento_id: str) -> SugestaoOwnership:
        documento = self._exigir_documento(documento_id)

        candidatos = self._calcular_candidatos(documento)
        if not candidatos:
            raise SemCandidatoOwnerError(
                f"Nao ha sinais historicos suficientes para sugerir owner de {documento_id}. "
                f"Atribua manualmente via aprovar_sugestao."
            )

        principal = candidatos[0]
        alternativos = tuple(candidatos[1:5])  # top 5 (4 alternativos)
        explicacao = self._gerar_explicacao(principal, len(candidatos))

        return SugestaoOwnership(
            documento_id=documento_id,
            candidato_principal=principal,
            candidatos_alternativos=alternativos,
            explicacao=explicacao,
        )

    def obter_owner(self, documento_id: str) -> Optional[OwnershipDocumento]:
        return self._owners.obter(documento_id)

    def listar_atribuidos(self) -> List[OwnershipDocumento]:
        return self._owners.listar()

    # ------------------------------------------------------------------
    # Decisao do aprovador
    # ------------------------------------------------------------------

    def aprovar_sugestao(
        self,
        documento_id: str,
        aprovador_id: str,
        owner_id: str,
        motivo: str = "",
    ) -> OwnershipDocumento:
        self._validar_strings(
            documento_id=documento_id, aprovador_id=aprovador_id, owner_id=owner_id,
        )
        self._exigir_documento(documento_id)

        existente = self._owners.obter(documento_id)
        if existente is not None:
            raise OwnershipJaAtribuidoError(
                f"Documento {documento_id} ja tem owner ({existente.owner_id}). "
                f"Use reatribuir."
            )

        ownership = OwnershipDocumento(
            documento_id=documento_id.strip(),
            owner_id=owner_id.strip(),
            atribuido_por=aprovador_id.strip(),
            fonte=FonteOwnership.SUGESTAO_ACEITA,
            motivo=(motivo or "").strip(),
        )
        self._owners.salvar(ownership)
        self._auditar_atribuicao(aprovador_id, ownership, primeira_vez=True)
        return ownership

    def reatribuir(
        self,
        documento_id: str,
        aprovador_id: str,
        novo_owner_id: str,
        motivo: str,
    ) -> OwnershipDocumento:
        self._validar_strings(
            documento_id=documento_id, aprovador_id=aprovador_id,
            novo_owner_id=novo_owner_id, motivo=motivo,
        )
        self._exigir_documento(documento_id)

        ownership = OwnershipDocumento(
            documento_id=documento_id.strip(),
            owner_id=novo_owner_id.strip(),
            atribuido_por=aprovador_id.strip(),
            fonte=FonteOwnership.MANUAL,
            motivo=motivo.strip(),
        )
        self._owners.salvar(ownership)
        self._auditar_atribuicao(aprovador_id, ownership, primeira_vez=False)
        return ownership

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calcular_candidatos(self, documento: DocumentoSubmetido) -> List[CandidatoOwner]:
        scores: Counter = Counter()
        eventos_por_usuario: Counter = Counter()

        for tipo_recurso in _TIPOS_RECURSO_DOC:
            registros = self._auditoria.consultar(FiltroAuditoria(
                tipo_recurso=tipo_recurso,
                recurso_id=documento.id,
                limite=500,
            ))
            for r in registros:
                peso = _PESOS_ACAO.get(r.tipo_acao, 0)
                if peso > 0:
                    scores[r.usuario_id] += peso
                    eventos_por_usuario[r.usuario_id] += 1

        # Fallback: se nao ha audit log mas o documento tem autor, ele eh candidato leve.
        if not scores and documento.autor_id:
            scores[documento.autor_id] = 1
            eventos_por_usuario[documento.autor_id] = 1

        candidatos = [
            CandidatoOwner(
                usuario_id=uid, score=score,
                eventos_considerados=eventos_por_usuario[uid],
                motivo=self._motivo_candidato(uid, eventos_por_usuario[uid], score, documento),
            )
            for uid, score in scores.most_common()
        ]
        return candidatos

    @staticmethod
    def _motivo_candidato(
        usuario_id: str, eventos: int, score: int, documento: DocumentoSubmetido,
    ) -> str:
        razoes = []
        if usuario_id == documento.autor_id:
            razoes.append("autor original do documento")
        razoes.append(f"{eventos} evento(s) na auditoria (score={score})")
        return "; ".join(razoes)

    def _gerar_explicacao(self, principal: CandidatoOwner, total_candidatos: int) -> str:
        return (
            f"Sugestao baseada em {total_candidatos} candidato(s) com sinais historicos. "
            f"Principal: '{principal.usuario_id}' com score {principal.score} "
            f"({principal.eventos_considerados} eventos)."
        )

    def _exigir_documento(self, documento_id: str) -> DocumentoSubmetido:
        if not documento_id or not documento_id.strip():
            raise DocumentoNaoEncontradoError("documento_id obrigatorio.")
        doc = self._docs.obter(documento_id.strip())
        if doc is None:
            raise DocumentoNaoEncontradoError(f"Documento {documento_id} nao existe.")
        return doc

    @staticmethod
    def _validar_strings(**campos: str) -> None:
        for nome, valor in campos.items():
            if not valor or not valor.strip():
                raise SugestaoOwnershipInvalidaError(f"campo '{nome}' e obrigatorio.")

    def _auditar_atribuicao(
        self, aprovador_id: str, ownership: OwnershipDocumento, primeira_vez: bool,
    ) -> None:
        self._auditoria.registrar_acao(
            usuario_id=aprovador_id,
            tipo_acao=TipoAcao.ATRIBUIU_PAPEL if primeira_vez else TipoAcao.EDITOU,
            tipo_recurso="ownership_documento",
            recurso_id=ownership.documento_id,
            detalhes={
                "owner_id": ownership.owner_id,
                "fonte": ownership.fonte.value,
                "motivo": ownership.motivo,
                "primeira_vez": primeira_vez,
            },
        )
