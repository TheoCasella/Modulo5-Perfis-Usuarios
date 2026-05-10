# Rotas REST para templates de aprovacao (US PU-04).

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.application.ports.driving.template_aprovacao_service import (
    TemplateAprovacaoService,
)
from app.config.composition_root import get_root
from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo
from app.domain.excecoes import (
    TemplateDuplicadoError,
    TemplateInvalidoError,
    TemplateNaoEncontradoError,
)


router = APIRouter(prefix="/api/templates-aprovacao", tags=["TemplatesAprovacao"])


def get_service() -> TemplateAprovacaoService:
    return get_root().get_template_aprovacao_service()


def _parse_papeis(papeis: List[str]) -> List[NomePapel]:
    try:
        return [NomePapel(p) for p in papeis]
    except ValueError as e:
        validos = ", ".join(p.value for p in NomePapel)
        raise HTTPException(
            status_code=400,
            detail=f"Papel invalido em {papeis}: {e}. Validos: {validos}.",
        )


def _parse_fluxo(fluxo: str) -> TipoFluxo:
    try:
        return TipoFluxo(fluxo)
    except ValueError:
        validos = ", ".join(f.value for f in TipoFluxo)
        raise HTTPException(
            status_code=400,
            detail=f"fluxo invalido: '{fluxo}'. Validos: {validos}.",
        )


class CriarTemplateRequest(BaseModel):
    projeto_id: str
    tipo_documento: str
    papeis_aprovadores: List[str] = Field(min_length=1)
    fluxo: str = "sequencial"
    criado_por: str


class AtualizarTemplateRequest(BaseModel):
    atualizado_por: str
    papeis_aprovadores: Optional[List[str]] = None
    fluxo: Optional[str] = None
    tipo_documento: Optional[str] = None


class AcaoUsuarioRequest(BaseModel):
    atualizado_por: str


class RemoverTemplateRequest(BaseModel):
    removido_por: str


@router.post("", status_code=201)
def criar(
    payload: CriarTemplateRequest,
    service: TemplateAprovacaoService = Depends(get_service),
):
    papeis = _parse_papeis(payload.papeis_aprovadores)
    fluxo = _parse_fluxo(payload.fluxo)
    try:
        t = service.criar(
            projeto_id=payload.projeto_id,
            tipo_documento=payload.tipo_documento,
            papeis_aprovadores=papeis,
            fluxo=fluxo,
            criado_por=payload.criado_por,
        )
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TemplateDuplicadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return t.to_dict()


@router.get("")
def listar(
    projeto_id: Optional[str] = Query(default=None),
    ativo: Optional[bool] = Query(default=None),
    service: TemplateAprovacaoService = Depends(get_service),
):
    items = service.listar(projeto_id=projeto_id, ativo=ativo)
    return {"templates": [t.to_dict() for t in items]}


@router.get("/{template_id}")
def obter(
    template_id: str,
    service: TemplateAprovacaoService = Depends(get_service),
):
    try:
        t = service.obter(template_id)
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return t.to_dict()


@router.put("/{template_id}")
def atualizar(
    template_id: str,
    payload: AtualizarTemplateRequest,
    service: TemplateAprovacaoService = Depends(get_service),
):
    papeis = _parse_papeis(payload.papeis_aprovadores) if payload.papeis_aprovadores else None
    fluxo = _parse_fluxo(payload.fluxo) if payload.fluxo else None
    try:
        t = service.atualizar(
            template_id=template_id,
            atualizado_por=payload.atualizado_por,
            papeis_aprovadores=papeis,
            fluxo=fluxo,
            tipo_documento=payload.tipo_documento,
        )
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return t.to_dict()


@router.post("/{template_id}/desativar")
def desativar(
    template_id: str,
    payload: AcaoUsuarioRequest,
    service: TemplateAprovacaoService = Depends(get_service),
):
    try:
        t = service.desativar(template_id, payload.atualizado_por)
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return t.to_dict()


@router.post("/{template_id}/reativar")
def reativar(
    template_id: str,
    payload: AcaoUsuarioRequest,
    service: TemplateAprovacaoService = Depends(get_service),
):
    try:
        t = service.reativar(template_id, payload.atualizado_por)
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateDuplicadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return t.to_dict()


@router.delete("/{template_id}", status_code=204)
def remover(
    template_id: str,
    removido_por: str = Query(..., description="ID do usuario que esta removendo"),
    service: TemplateAprovacaoService = Depends(get_service),
):
    try:
        service.remover(template_id, removido_por)
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None


@router.get("/{template_id}/papeis-pendentes")
def papeis_pendentes(
    template_id: str,
    aprovados: List[str] = Query(default=[], description="Papeis que ja aprovaram"),
    service: TemplateAprovacaoService = Depends(get_service),
):
    papeis_aprovados = _parse_papeis(aprovados)
    try:
        pendentes = service.papeis_pendentes(template_id, papeis_aprovados)
    except TemplateNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"pendentes": [p.value for p in pendentes]}
