# Porta driving: TemplateAprovacaoService (US PU-04)

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from app.domain.entidades.template_aprovacao import (
    NomePapel,
    TemplateAprovacao,
    TipoFluxo,
)


class TemplateAprovacaoService(ABC):

    @abstractmethod
    def criar(
        self,
        projeto_id: str,
        tipo_documento: str,
        papeis_aprovadores: Iterable[NomePapel],
        fluxo: TipoFluxo,
        criado_por: str,
    ) -> TemplateAprovacao:
        pass

    @abstractmethod
    def atualizar(
        self,
        template_id: str,
        atualizado_por: str,
        papeis_aprovadores: Optional[Iterable[NomePapel]] = None,
        fluxo: Optional[TipoFluxo] = None,
        tipo_documento: Optional[str] = None,
    ) -> TemplateAprovacao:
        pass

    @abstractmethod
    def desativar(self, template_id: str, atualizado_por: str) -> TemplateAprovacao:
        pass

    @abstractmethod
    def reativar(self, template_id: str, atualizado_por: str) -> TemplateAprovacao:
        pass

    @abstractmethod
    def remover(self, template_id: str, removido_por: str) -> None:
        pass

    @abstractmethod
    def obter(self, template_id: str) -> TemplateAprovacao:
        pass

    @abstractmethod
    def listar(
        self,
        projeto_id: Optional[str] = None,
        ativo: Optional[bool] = None,
    ) -> List[TemplateAprovacao]:
        pass

    @abstractmethod
    def papeis_pendentes(
        self,
        template_id: str,
        papeis_ja_aprovaram: Iterable[NomePapel],
    ) -> List[NomePapel]:
        """
        Calcula quais papeis ainda precisam aprovar segundo o fluxo do template.
        Base para o fluxo automatizado de PU-05.
        """
        pass
