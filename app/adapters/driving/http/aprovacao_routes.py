# Rotas HTTP para o fluxo de aprovacao (US PU-05).

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.ports.driving.aprovacao_service import AprovacaoService
from app.config.composition_root import get_root
from app.domain.entidades.template_aprovacao import NomePapel
from app.domain.excecoes import (
    AprovacaoDuplicadaError,
    AprovacaoForaDeOrdemError,
    DocumentoDuplicadoError,
    DocumentoFinalizadoError,
    DocumentoNaoEncontradoError,
    TemplateInvalidoError,
    TemplateNaoEncontradoError,
)


router = APIRouter(prefix="/api/documentos", tags=["Aprovacao"])


def get_service() -> AprovacaoService:
    return get_root().get_aprovacao_service()


def _parse_papel(valor: str) -> NomePapel:
    try:
        return NomePapel(valor)
    except ValueError:
        validos = ", ".join(p.value for p in NomePapel)
        raise HTTPException(status_code=400, detail=f"Papel invalido: '{valor}'. Validos: {validos}.")


class SubmeterRequest(BaseModel):
    documento_id: str
    projeto_id: str
    tipo_documento: str
    autor_id: str
    titulo: str


class DecisaoRequest(BaseModel):
    aprovador_id: str
    papel: str
    comentario: str = ""


class CancelarRequest(BaseModel):
    autor_id: str
    motivo: str = ""


@router.post("/submeter", status_code=201)
def submeter(payload: SubmeterRequest, service: AprovacaoService = Depends(get_service)):
    try:
        doc = service.submeter(
            documento_id=payload.documento_id,
            projeto_id=payload.projeto_id,
            tipo_documento=payload.tipo_documento,
            autor_id=payload.autor_id,
            titulo=payload.titulo,
        )
    except DocumentoDuplicadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=412, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return doc.to_dict()


@router.post("/{documento_id}/aprovar", status_code=201)
def aprovar(documento_id: str, payload: DecisaoRequest, service: AprovacaoService = Depends(get_service)):
    papel = _parse_papel(payload.papel)
    try:
        decisao = service.aprovar(documento_id, payload.aprovador_id, papel, payload.comentario)
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentoFinalizadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AprovacaoDuplicadaError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AprovacaoForaDeOrdemError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return decisao.to_dict()


@router.post("/{documento_id}/rejeitar", status_code=201)
def rejeitar(documento_id: str, payload: DecisaoRequest, service: AprovacaoService = Depends(get_service)):
    papel = _parse_papel(payload.papel)
    try:
        decisao = service.rejeitar(documento_id, payload.aprovador_id, papel, payload.comentario)
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentoFinalizadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AprovacaoDuplicadaError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AprovacaoForaDeOrdemError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return decisao.to_dict()


@router.post("/{documento_id}/cancelar")
def cancelar(documento_id: str, payload: CancelarRequest, service: AprovacaoService = Depends(get_service)):
    try:
        doc = service.cancelar(documento_id, payload.autor_id, payload.motivo)
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentoFinalizadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AprovacaoForaDeOrdemError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return doc.to_dict()


@router.get("/{documento_id}")
def consultar(documento_id: str, service: AprovacaoService = Depends(get_service)):
    try:
        status = service.consultar(documento_id)
    except DocumentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return status.to_dict()


@router.get("/pendentes/por-papel")
def fila_pendente(
    papel: str = Query(..., description="Papel do aprovador, ex: tech_lead"),
    service: AprovacaoService = Depends(get_service),
):
    nome_papel = _parse_papel(papel)
    fila = service.fila_pendente(nome_papel)
    return {"pendentes": [s.to_dict() for s in fila]}
