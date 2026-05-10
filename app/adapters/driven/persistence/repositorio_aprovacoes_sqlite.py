# Repositorio SQLite para aprovacoes/decisoes — append-only (US PU-05).

import sqlite3
import threading
from datetime import datetime
from typing import List

from app.application.ports.driven.repositorio_aprovacoes import RepositorioAprovacoes
from app.domain.entidades.aprovacao import Aprovacao, Decisao
from app.domain.entidades.template_aprovacao import NomePapel


_SCHEMA = """
CREATE TABLE IF NOT EXISTS aprovacoes (
    id TEXT PRIMARY KEY,
    documento_id TEXT NOT NULL,
    aprovador_id TEXT NOT NULL,
    papel TEXT NOT NULL,
    decisao TEXT NOT NULL,
    comentario TEXT NOT NULL DEFAULT '',
    decidido_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_aprov_doc ON aprovacoes(documento_id);
"""


class RepositorioAprovacoesSQLite(RepositorioAprovacoes):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def registrar(self, aprovacao: Aprovacao) -> None:
        sql = """
            INSERT INTO aprovacoes (id, documento_id, aprovador_id, papel, decisao, comentario, decidido_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock:
            try:
                self._conexao.execute(sql, (
                    aprovacao.id,
                    aprovacao.documento_id,
                    aprovacao.aprovador_id,
                    aprovacao.papel.value,
                    aprovacao.decisao.value,
                    aprovacao.comentario,
                    aprovacao.decidido_em.isoformat(),
                ))
                self._conexao.commit()
            except sqlite3.IntegrityError as e:
                raise ValueError(f"Aprovacao com id {aprovacao.id} ja existe.") from e

    def listar_por_documento(self, documento_id: str) -> List[Aprovacao]:
        with self._lock:
            linhas = self._conexao.execute(
                "SELECT * FROM aprovacoes WHERE documento_id = ? ORDER BY decidido_em ASC",
                (documento_id,),
            ).fetchall()
        return [self._linha_para_entidade(linha) for linha in linhas]

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_entidade(linha: sqlite3.Row) -> Aprovacao:
        return Aprovacao(
            id=linha["id"],
            documento_id=linha["documento_id"],
            aprovador_id=linha["aprovador_id"],
            papel=NomePapel(linha["papel"]),
            decisao=Decisao(linha["decisao"]),
            comentario=linha["comentario"] or "",
            decidido_em=datetime.fromisoformat(linha["decidido_em"]),
        )
