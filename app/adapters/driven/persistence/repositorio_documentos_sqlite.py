# Repositorio SQLite para documentos submetidos (US PU-05).

import json
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

from app.application.ports.driven.repositorio_documentos import RepositorioDocumentos
from app.domain.entidades.aprovacao import DocumentoSubmetido, StatusAprovacao
from app.domain.entidades.template_aprovacao import NomePapel, TipoFluxo


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documentos_submetidos (
    id TEXT PRIMARY KEY,
    projeto_id TEXT NOT NULL,
    tipo_documento TEXT NOT NULL,
    autor_id TEXT NOT NULL,
    titulo TEXT NOT NULL,
    template_id TEXT NOT NULL,
    papeis_aprovadores TEXT NOT NULL,
    fluxo TEXT NOT NULL,
    status TEXT NOT NULL,
    submetido_em TEXT NOT NULL,
    finalizado_em TEXT,
    motivo_cancelamento TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_projeto ON documentos_submetidos(projeto_id);
CREATE INDEX IF NOT EXISTS idx_doc_status ON documentos_submetidos(status);
"""


class RepositorioDocumentosSQLite(RepositorioDocumentos):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def salvar(self, documento: DocumentoSubmetido) -> None:
        sql = """
            INSERT INTO documentos_submetidos
                (id, projeto_id, tipo_documento, autor_id, titulo, template_id,
                 papeis_aprovadores, fluxo, status, submetido_em, finalizado_em, motivo_cancelamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                finalizado_em = excluded.finalizado_em,
                motivo_cancelamento = excluded.motivo_cancelamento
        """
        valores = (
            documento.id,
            documento.projeto_id,
            documento.tipo_documento,
            documento.autor_id,
            documento.titulo,
            documento.template_id,
            json.dumps([p.value for p in documento.papeis_aprovadores]),
            documento.fluxo.value,
            documento.status.value,
            documento.submetido_em.isoformat(),
            documento.finalizado_em.isoformat() if documento.finalizado_em else None,
            documento.motivo_cancelamento,
        )
        with self._lock:
            self._conexao.execute(sql, valores)
            self._conexao.commit()

    def obter(self, documento_id: str) -> Optional[DocumentoSubmetido]:
        with self._lock:
            linha = self._conexao.execute(
                "SELECT * FROM documentos_submetidos WHERE id = ?", (documento_id,)
            ).fetchone()
        return self._linha_para_entidade(linha) if linha else None

    def listar(
        self,
        projeto_id: Optional[str] = None,
        status: Optional[StatusAprovacao] = None,
    ) -> List[DocumentoSubmetido]:
        clausulas: list = []
        valores: list = []
        if projeto_id is not None:
            clausulas.append("projeto_id = ?")
            valores.append(projeto_id)
        if status is not None:
            clausulas.append("status = ?")
            valores.append(status.value)

        sql = "SELECT * FROM documentos_submetidos"
        if clausulas:
            sql += " WHERE " + " AND ".join(clausulas)
        sql += " ORDER BY submetido_em DESC"

        with self._lock:
            linhas = self._conexao.execute(sql, valores).fetchall()
        return [self._linha_para_entidade(linha) for linha in linhas]

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_entidade(linha: sqlite3.Row) -> DocumentoSubmetido:
        papeis = tuple(NomePapel(p) for p in json.loads(linha["papeis_aprovadores"]))
        return DocumentoSubmetido(
            id=linha["id"],
            projeto_id=linha["projeto_id"],
            tipo_documento=linha["tipo_documento"],
            autor_id=linha["autor_id"],
            titulo=linha["titulo"],
            template_id=linha["template_id"],
            papeis_aprovadores=papeis,
            fluxo=TipoFluxo(linha["fluxo"]),
            status=StatusAprovacao(linha["status"]),
            submetido_em=datetime.fromisoformat(linha["submetido_em"]),
            finalizado_em=datetime.fromisoformat(linha["finalizado_em"]) if linha["finalizado_em"] else None,
            motivo_cancelamento=linha["motivo_cancelamento"],
        )
