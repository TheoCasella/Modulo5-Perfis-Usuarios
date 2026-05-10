# Porta driving: AprovacaoService (US PU-05)

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from app.domain.entidades.aprovacao import Aprovacao, DocumentoSubmetido
from app.domain.entidades.template_aprovacao import NomePapel


@dataclass(frozen=True)
class StatusDocumento:
    documento: DocumentoSubmetido
    decisoes: List[Aprovacao]

    def to_dict(self) -> dict:
        return self.documento.to_dict(self.decisoes)


class AprovacaoService(ABC):

    @abstractmethod
    def submeter(
        self,
        documento_id: str,
        projeto_id: str,
        tipo_documento: str,
        autor_id: str,
        titulo: str,
    ) -> DocumentoSubmetido:
        """Submete um doc para aprovacao usando o template ativo do projeto."""
        pass

    @abstractmethod
    def aprovar(
        self,
        documento_id: str,
        aprovador_id: str,
        papel: NomePapel,
        comentario: str = "",
    ) -> Aprovacao:
        pass

    @abstractmethod
    def rejeitar(
        self,
        documento_id: str,
        aprovador_id: str,
        papel: NomePapel,
        comentario: str = "",
    ) -> Aprovacao:
        pass

    @abstractmethod
    def cancelar(
        self,
        documento_id: str,
        autor_id: str,
        motivo: str = "",
    ) -> DocumentoSubmetido:
        pass

    @abstractmethod
    def consultar(self, documento_id: str) -> StatusDocumento:
        pass

    @abstractmethod
    def fila_pendente(self, papel: NomePapel) -> List[StatusDocumento]:
        """Documentos PENDENTES aguardando uma decisao desse papel."""
        pass
