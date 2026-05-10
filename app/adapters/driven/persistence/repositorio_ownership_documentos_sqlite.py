# Repositorio SQLite para ownership de documentos (US PU-03).

import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Set

from app.application.ports.driven.repositorio_ownership_documentos import (
    RepositorioOwnershipDocumentos,
)
from app.domain.entidades.ownership_documento import FonteOwnership, OwnershipDocumento


_SCHEMA = """
CREATE TABLE IF NOT EXISTS ownership_documentos (
    documento_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    atribuido_por TEXT NOT NULL,
    fonte TEXT NOT NULL,
    motivo TEXT NOT NULL DEFAULT '',
    atribuido_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_owner_doc_owner ON ownership_documentos(owner_id);
"""


class RepositorioOwnershipDocumentosSQLite(RepositorioOwnershipDocumentos):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def salvar(self, ownership: OwnershipDocumento) -> None:
        sql = """
            INSERT INTO ownership_documentos
                (documento_id, owner_id, atribuido_por, fonte, motivo, atribuido_em)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(documento_id) DO UPDATE SET
                owner_id = excluded.owner_id,
                atribuido_por = excluded.atribuido_por,
                fonte = excluded.fonte,
                motivo = excluded.motivo,
                atribuido_em = excluded.atribuido_em
        """
        with self._lock:
            self._conexao.execute(sql, (
                ownership.documento_id, ownership.owner_id, ownership.atribuido_por,
                ownership.fonte.value, ownership.motivo, ownership.atribuido_em.isoformat(),
            ))
            self._conexao.commit()

    def obter(self, documento_id: str) -> Optional[OwnershipDocumento]:
        with self._lock:
            linha = self._conexao.execute(
                "SELECT * FROM ownership_documentos WHERE documento_id = ?", (documento_id,),
            ).fetchone()
        return self._linha_para_ownership(linha) if linha else None

    def listar(self) -> List[OwnershipDocumento]:
        with self._lock:
            linhas = self._conexao.execute(
                "SELECT * FROM ownership_documentos ORDER BY atribuido_em DESC",
            ).fetchall()
        return [self._linha_para_ownership(l) for l in linhas]

    def documentos_com_owner(self) -> Set[str]:
        with self._lock:
            linhas = self._conexao.execute(
                "SELECT documento_id FROM ownership_documentos",
            ).fetchall()
        return {l["documento_id"] for l in linhas}

    def remover(self, documento_id: str) -> bool:
        with self._lock:
            cur = self._conexao.execute(
                "DELETE FROM ownership_documentos WHERE documento_id = ?", (documento_id,),
            )
            self._conexao.commit()
            return cur.rowcount > 0

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_ownership(linha: sqlite3.Row) -> OwnershipDocumento:
        return OwnershipDocumento(
            documento_id=linha["documento_id"],
            owner_id=linha["owner_id"],
            atribuido_por=linha["atribuido_por"],
            fonte=FonteOwnership(linha["fonte"]),
            motivo=linha["motivo"] or "",
            atribuido_em=datetime.fromisoformat(linha["atribuido_em"]),
        )
