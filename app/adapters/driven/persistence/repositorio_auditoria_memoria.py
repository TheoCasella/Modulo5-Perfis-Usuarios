# Repositorio de auditoria em memoria — para testes e dev rapido.
# Nao persiste entre restarts.

import threading
from typing import Dict, List

from app.application.ports.driven.repositorio_auditoria import RepositorioAuditoria
from app.domain.entidades.registro_auditoria import FiltroAuditoria, RegistroAuditoria


class RepositorioAuditoriaMemoria(RepositorioAuditoria):

    def __init__(self):
        self._registros: Dict[str, RegistroAuditoria] = {}
        self._lock = threading.Lock()

    def registrar(self, registro: RegistroAuditoria) -> None:
        with self._lock:
            if registro.id in self._registros:
                raise ValueError(f"Registro com id {registro.id} ja existe.")
            self._registros[registro.id] = registro

    def consultar(self, filtros: FiltroAuditoria) -> List[RegistroAuditoria]:
        with self._lock:
            candidatos = list(self._registros.values())

        def passa(r: RegistroAuditoria) -> bool:
            if filtros.usuario_id is not None and r.usuario_id != filtros.usuario_id:
                return False
            if filtros.tipo_acao is not None and r.tipo_acao != filtros.tipo_acao:
                return False
            if filtros.tipo_recurso is not None and r.tipo_recurso != filtros.tipo_recurso:
                return False
            if filtros.recurso_id is not None and r.recurso_id != filtros.recurso_id:
                return False
            if filtros.desde is not None and r.timestamp < filtros.desde:
                return False
            if filtros.ate is not None and r.timestamp > filtros.ate:
                return False
            return True

        casados = [r for r in candidatos if passa(r)]
        casados.sort(key=lambda r: r.timestamp, reverse=True)
        return casados[: filtros.limite]
