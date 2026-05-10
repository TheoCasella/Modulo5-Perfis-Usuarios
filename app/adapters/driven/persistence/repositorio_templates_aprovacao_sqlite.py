# Repositorio de templates de aprovacao em SQLite (US PU-04).

import json
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

from app.application.ports.driven.repositorio_templates_aprovacao import (
    RepositorioTemplatesAprovacao,
)
from app.domain.entidades.template_aprovacao import (
    NomePapel,
    TemplateAprovacao,
    TipoFluxo,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS templates_aprovacao (
    id TEXT PRIMARY KEY,
    projeto_id TEXT NOT NULL,
    tipo_documento TEXT NOT NULL,
    papeis_aprovadores TEXT NOT NULL,  -- JSON list of NomePapel.value
    fluxo TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_por TEXT NOT NULL,
    atualizado_por TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_template_projeto ON templates_aprovacao(projeto_id);
CREATE INDEX IF NOT EXISTS idx_template_projeto_tipo_ativo ON templates_aprovacao(projeto_id, tipo_documento, ativo);
"""


class RepositorioTemplatesAprovacaoSQLite(RepositorioTemplatesAprovacao):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    def salvar(self, template: TemplateAprovacao) -> None:
        sql = """
            INSERT INTO templates_aprovacao
                (id, projeto_id, tipo_documento, papeis_aprovadores, fluxo, ativo,
                 criado_por, atualizado_por, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                projeto_id = excluded.projeto_id,
                tipo_documento = excluded.tipo_documento,
                papeis_aprovadores = excluded.papeis_aprovadores,
                fluxo = excluded.fluxo,
                ativo = excluded.ativo,
                atualizado_por = excluded.atualizado_por,
                atualizado_em = excluded.atualizado_em
        """
        valores = (
            template.id,
            template.projeto_id,
            template.tipo_documento,
            json.dumps([p.value for p in template.papeis_aprovadores], ensure_ascii=False),
            template.fluxo.value,
            1 if template.ativo else 0,
            template.criado_por,
            template.atualizado_por,
            template.criado_em.isoformat(),
            template.atualizado_em.isoformat(),
        )
        with self._lock:
            self._conexao.execute(sql, valores)
            self._conexao.commit()

    def obter(self, template_id: str) -> Optional[TemplateAprovacao]:
        with self._lock:
            linha = self._conexao.execute(
                "SELECT * FROM templates_aprovacao WHERE id = ?", (template_id,)
            ).fetchone()
        return self._linha_para_entidade(linha) if linha else None

    def listar(
        self,
        projeto_id: Optional[str] = None,
        ativo: Optional[bool] = None,
    ) -> List[TemplateAprovacao]:
        clausulas: list = []
        valores: list = []
        if projeto_id is not None:
            clausulas.append("projeto_id = ?")
            valores.append(projeto_id)
        if ativo is not None:
            clausulas.append("ativo = ?")
            valores.append(1 if ativo else 0)

        sql = "SELECT * FROM templates_aprovacao"
        if clausulas:
            sql += " WHERE " + " AND ".join(clausulas)
        sql += " ORDER BY projeto_id, tipo_documento, atualizado_em DESC"
        with self._lock:
            linhas = self._conexao.execute(sql, valores).fetchall()
        return [self._linha_para_entidade(linha) for linha in linhas]

    def encontrar_ativo(
        self, projeto_id: str, tipo_documento: str
    ) -> Optional[TemplateAprovacao]:
        sql = """
            SELECT * FROM templates_aprovacao
            WHERE projeto_id = ? AND tipo_documento = ? AND ativo = 1
            ORDER BY atualizado_em DESC LIMIT 1
        """
        with self._lock:
            linha = self._conexao.execute(sql, (projeto_id, tipo_documento)).fetchone()
        return self._linha_para_entidade(linha) if linha else None

    def remover(self, template_id: str) -> bool:
        with self._lock:
            cursor = self._conexao.execute(
                "DELETE FROM templates_aprovacao WHERE id = ?", (template_id,)
            )
            self._conexao.commit()
            return cursor.rowcount > 0

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_entidade(linha: sqlite3.Row) -> TemplateAprovacao:
        papeis_str = json.loads(linha["papeis_aprovadores"])
        return TemplateAprovacao(
            id=linha["id"],
            projeto_id=linha["projeto_id"],
            tipo_documento=linha["tipo_documento"],
            papeis_aprovadores=tuple(NomePapel(p) for p in papeis_str),
            fluxo=TipoFluxo(linha["fluxo"]),
            ativo=bool(linha["ativo"]),
            criado_por=linha["criado_por"],
            atualizado_por=linha["atualizado_por"],
            criado_em=datetime.fromisoformat(linha["criado_em"]),
            atualizado_em=datetime.fromisoformat(linha["atualizado_em"]),
        )
