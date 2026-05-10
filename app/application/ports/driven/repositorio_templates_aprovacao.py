# Porta driven: RepositorioTemplatesAprovacao (US PU-04)

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entidades.template_aprovacao import TemplateAprovacao


class RepositorioTemplatesAprovacao(ABC):

    @abstractmethod
    def salvar(self, template: TemplateAprovacao) -> None:
        """Insere ou atualiza (upsert por id)."""
        pass

    @abstractmethod
    def obter(self, template_id: str) -> Optional[TemplateAprovacao]:
        pass

    @abstractmethod
    def listar(
        self,
        projeto_id: Optional[str] = None,
        ativo: Optional[bool] = None,
    ) -> List[TemplateAprovacao]:
        pass

    @abstractmethod
    def encontrar_ativo(
        self, projeto_id: str, tipo_documento: str
    ) -> Optional[TemplateAprovacao]:
        """Util para PU-05: dado um doc, qual template ativo aplicar?"""
        pass

    @abstractmethod
    def remover(self, template_id: str) -> bool:
        """Remove fisicamente. Retorna True se removeu, False se nao existia."""
        pass
