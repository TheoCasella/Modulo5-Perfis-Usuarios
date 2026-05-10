# Implementacao do AuditoriaService — orquestra o repositorio (US PU-06).

from typing import Any, Dict, List, Optional

from app.application.ports.driven.repositorio_auditoria import RepositorioAuditoria
from app.application.ports.driving.auditoria_service import AuditoriaService
from app.domain.entidades.registro_auditoria import (
    FiltroAuditoria,
    RegistroAuditoria,
    TipoAcao,
)
from app.domain.excecoes import AuditoriaInvalidaError, FiltroAuditoriaInvalidoError


class AuditoriaServiceImpl(AuditoriaService):

    def __init__(self, repositorio: RepositorioAuditoria):
        self._repositorio = repositorio

    def registrar_acao(
        self,
        usuario_id: str,
        tipo_acao: TipoAcao,
        tipo_recurso: str,
        recurso_id: str,
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> RegistroAuditoria:
        if not usuario_id or not usuario_id.strip():
            raise AuditoriaInvalidaError("usuario_id e obrigatorio.")
        if not tipo_recurso or not tipo_recurso.strip():
            raise AuditoriaInvalidaError("tipo_recurso e obrigatorio.")
        if not recurso_id or not recurso_id.strip():
            raise AuditoriaInvalidaError("recurso_id e obrigatorio.")

        registro = RegistroAuditoria(
            usuario_id=usuario_id.strip(),
            tipo_acao=tipo_acao,
            tipo_recurso=tipo_recurso.strip(),
            recurso_id=recurso_id.strip(),
            detalhes=detalhes or {},
        )
        self._repositorio.registrar(registro)
        return registro

    def consultar(self, filtros: FiltroAuditoria) -> List[RegistroAuditoria]:
        if filtros.desde is not None and filtros.ate is not None and filtros.ate < filtros.desde:
            raise FiltroAuditoriaInvalidoError("'ate' nao pode ser anterior a 'desde'.")
        if filtros.limite <= 0:
            raise FiltroAuditoriaInvalidoError("'limite' deve ser positivo.")
        return self._repositorio.consultar(filtros)
