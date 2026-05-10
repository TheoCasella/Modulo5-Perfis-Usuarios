# Repositorio de ownership persistente em SQLite (US PU-09).
# Upsert por (repositorio, modulo); guarda timestamp para o service decidir staleness.

import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

from app.application.ports.driven.repositorio_ownership import RepositorioOwnership
from app.domain.entidades.ownership import Ownership


_SCHEMA = """
CREATE TABLE IF NOT EXISTS ownership (
    repositorio TEXT NOT NULL,
    modulo TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    confianca REAL NOT NULL,
    total_commits INTEGER NOT NULL DEFAULT 0,
    ultima_atualizacao TEXT NOT NULL,
    PRIMARY KEY (repositorio, modulo)
);
CREATE INDEX IF NOT EXISTS idx_ownership_repo ON ownership(repositorio);
"""


class RepositorioOwnershipSQLite(RepositorioOwnership):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def salvar(self, ownership: Ownership) -> None:
        sql = """
            INSERT INTO ownership (repositorio, modulo, owner_id, confianca, total_commits, ultima_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repositorio, modulo) DO UPDATE SET
                owner_id = excluded.owner_id,
                confianca = excluded.confianca,
                total_commits = excluded.total_commits,
                ultima_atualizacao = excluded.ultima_atualizacao
        """
        with self._lock:
            self._conexao.execute(
                sql,
                (
                    ownership.repositorio,
                    ownership.modulo,
                    ownership.owner_id,
                    ownership.confianca,
                    ownership.total_commits,
                    ownership.ultima_atualizacao.isoformat(),
                ),
            )
            self._conexao.commit()

    def obter(self, repositorio: str, modulo: str) -> Optional[Ownership]:
        sql = "SELECT * FROM ownership WHERE repositorio = ? AND modulo = ?"
        with self._lock:
            cursor = self._conexao.execute(sql, (repositorio, modulo))
            linha = cursor.fetchone()
        return self._linha_para_ownership(linha) if linha else None

    def listar(self, repositorio: Optional[str] = None) -> List[Ownership]:
        if repositorio is not None:
            sql = "SELECT * FROM ownership WHERE repositorio = ? ORDER BY modulo"
            args = (repositorio,)
        else:
            sql = "SELECT * FROM ownership ORDER BY repositorio, modulo"
            args = ()
        with self._lock:
            linhas = self._conexao.execute(sql, args).fetchall()
        return [self._linha_para_ownership(linha) for linha in linhas]

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_ownership(linha: sqlite3.Row) -> Ownership:
        return Ownership(
            repositorio=linha["repositorio"],
            modulo=linha["modulo"],
            owner_id=linha["owner_id"],
            confianca=float(linha["confianca"]),
            total_commits=int(linha["total_commits"]),
            ultima_atualizacao=datetime.fromisoformat(linha["ultima_atualizacao"]),
        )
