# Porta driving: SugestaoOwnershipService (US PU-03)

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entidades.aprovacao import DocumentoSubmetido
from app.domain.entidades.ownership_documento import (
    OwnershipDocumento,
    SugestaoOwnership,
)


class SugestaoOwnershipService(ABC):

    @abstractmethod
    def listar_orfaos(self, projeto_id: Optional[str] = None) -> List[DocumentoSubmetido]:
        """Documentos PU-05 que ainda nao tem OwnershipDocumento atribuido."""
        pass

    @abstractmethod
    def sugerir(self, documento_id: str) -> SugestaoOwnership:
        """
        Calcula o melhor candidato a owner com base em sinais historicos:
          - Audit log do documento (PU-06): quem CRIOU/EDITOU/COMENTOU
          - Fallback: autor_id do documento (PU-05)
        Levanta SemCandidatoOwnerError se nada for encontrado.
        Levanta DocumentoNaoEncontradoError se o doc nao existir.
        """
        pass

    @abstractmethod
    def aprovar_sugestao(
        self,
        documento_id: str,
        aprovador_id: str,
        owner_id: str,
        motivo: str = "",
    ) -> OwnershipDocumento:
        """
        Aprovador decide quem sera o owner. Pode aceitar a sugestao (passando o
        candidato_principal) ou escolher outro usuario.
        Audita a decisao via PU-06.
        Levanta OwnershipJaAtribuidoError se ja existir owner — use reatribuir.
        """
        pass

    @abstractmethod
    def reatribuir(
        self,
        documento_id: str,
        aprovador_id: str,
        novo_owner_id: str,
        motivo: str,
    ) -> OwnershipDocumento:
        """Substitui owner existente. Motivo eh obrigatorio (auditoria)."""
        pass

    @abstractmethod
    def obter_owner(self, documento_id: str) -> Optional[OwnershipDocumento]:
        pass

    @abstractmethod
    def listar_atribuidos(self) -> List[OwnershipDocumento]:
        pass
