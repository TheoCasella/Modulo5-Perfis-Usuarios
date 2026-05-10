# Repositorio de auditoria persistente em SQLite (stdlib sqlite3 — sem ORM).
# Append-only: somente INSERT e SELECT. Nada de UPDATE/DELETE no port.

import json
import sqlite3
import threading
from datetime import datetime
from typing import List

from app.application.ports.driven.repositorio_auditoria import RepositorioAuditoria
from app.domain.entidades.registro_auditoria import (
    FiltroAuditoria,
    RegistroAuditoria,
    TipoAcao,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS auditoria (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    tipo_acao TEXT NOT NULL,
    tipo_recurso TEXT NOT NULL,
    recurso_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    detalhes TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_recurso ON auditoria(tipo_recurso, recurso_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_timestamp ON auditoria(timestamp);
"""


class RepositorioAuditoriaSQLite(RepositorioAuditoria):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        # check_same_thread=False porque o FastAPI pode chamar de threads diferentes.
        # Lock garante exclusao mutua nas escritas (sqlite3 nao eh re-entrant safe sem isso).
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def registrar(self, registro: RegistroAuditoria) -> None:
        sql = """
            INSERT INTO auditoria (id, usuario_id, tipo_acao, tipo_recurso, recurso_id, timestamp, detalhes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock:
            try:
                self._conexao.execute(
                    sql,
                    (
                        registro.id,
                        registro.usuario_id,
                        registro.tipo_acao.value,
                        registro.tipo_recurso,
                        registro.recurso_id,
                        registro.timestamp.isoformat(),
                        json.dumps(registro.detalhes, ensure_ascii=False),
                    ),
                )
                self._conexao.commit()
            except sqlite3.IntegrityError as e:
                raise ValueError(f"Registro com id {registro.id} ja existe.") from e

    def consultar(self, filtros: FiltroAuditoria) -> List[RegistroAuditoria]:
        clausulas = []
        valores: list = []

        if filtros.usuario_id is not None:
            clausulas.append("usuario_id = ?")
            valores.append(filtros.usuario_id)
        if filtros.tipo_acao is not None:
            clausulas.append("tipo_acao = ?")
            valores.append(filtros.tipo_acao.value)
        if filtros.tipo_recurso is not None:
            clausulas.append("tipo_recurso = ?")
            valores.append(filtros.tipo_recurso)
        if filtros.recurso_id is not None:
            clausulas.append("recurso_id = ?")
            valores.append(filtros.recurso_id)
        if filtros.desde is not None:
            clausulas.append("timestamp >= ?")
            valores.append(filtros.desde.isoformat())
        if filtros.ate is not None:
            clausulas.append("timestamp <= ?")
            valores.append(filtros.ate.isoformat())

        sql = "SELECT * FROM auditoria"
        if clausulas:
            sql += " WHERE " + " AND ".join(clausulas)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        valores.append(filtros.limite)

        with self._lock:
            cursor = self._conexao.execute(sql, valores)
            linhas = cursor.fetchall()

        return [self._linha_para_registro(linha) for linha in linhas]

    @staticmethod
    def _linha_para_registro(linha: sqlite3.Row) -> RegistroAuditoria:
        return RegistroAuditoria(
            id=linha["id"],
            usuario_id=linha["usuario_id"],
            tipo_acao=TipoAcao(linha["tipo_acao"]),
            tipo_recurso=linha["tipo_recurso"],
            recurso_id=linha["recurso_id"],
            timestamp=datetime.fromisoformat(linha["timestamp"]),
            detalhes=json.loads(linha["detalhes"]),
        )

    def fechar(self):
        with self._lock:
            self._conexao.close()
