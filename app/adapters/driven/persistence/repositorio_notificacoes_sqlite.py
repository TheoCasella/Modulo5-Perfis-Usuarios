# Repositorio SQLite para subscricoes e notificacoes (US PU-07).

import json
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

from app.application.ports.driven.repositorio_notificacoes import (
    RepositorioNotificacoes,
)
from app.domain.entidades.notificacao import (
    Notificacao,
    Subscricao,
    TipoEventoNotificacao,
)
from app.domain.excecoes import SubscricaoDuplicadaError


_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscricoes (
    usuario_id TEXT NOT NULL,
    documento_id TEXT NOT NULL,
    criada_em TEXT NOT NULL,
    PRIMARY KEY (usuario_id, documento_id)
);
CREATE INDEX IF NOT EXISTS idx_sub_doc ON subscricoes(documento_id);
CREATE INDEX IF NOT EXISTS idx_sub_user ON subscricoes(usuario_id);

CREATE TABLE IF NOT EXISTS notificacoes (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    documento_id TEXT NOT NULL,
    tipo_evento TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    detalhes TEXT NOT NULL DEFAULT '{}',
    lida INTEGER NOT NULL DEFAULT 0,
    criada_em TEXT NOT NULL,
    lida_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_notif_usuario_lida ON notificacoes(usuario_id, lida);
CREATE INDEX IF NOT EXISTS idx_notif_documento ON notificacoes(documento_id);
"""


class RepositorioNotificacoesSQLite(RepositorioNotificacoes):

    def __init__(self, caminho_db: str):
        self._caminho = caminho_db
        self._conexao = sqlite3.connect(caminho_db, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conexao.executescript(_SCHEMA)
            self._conexao.commit()

    # --- Subscricoes ---

    def adicionar_subscricao(self, subscricao: Subscricao) -> None:
        sql = "INSERT INTO subscricoes (usuario_id, documento_id, criada_em) VALUES (?, ?, ?)"
        with self._lock:
            try:
                self._conexao.execute(sql, (
                    subscricao.usuario_id, subscricao.documento_id,
                    subscricao.criada_em.isoformat(),
                ))
                self._conexao.commit()
            except sqlite3.IntegrityError as e:
                raise SubscricaoDuplicadaError(
                    f"Usuario {subscricao.usuario_id} ja segue documento {subscricao.documento_id}."
                ) from e

    def remover_subscricao(self, usuario_id: str, documento_id: str) -> bool:
        with self._lock:
            cur = self._conexao.execute(
                "DELETE FROM subscricoes WHERE usuario_id = ? AND documento_id = ?",
                (usuario_id, documento_id),
            )
            self._conexao.commit()
            return cur.rowcount > 0

    def listar_seguidores(self, documento_id: str) -> List[str]:
        with self._lock:
            linhas = self._conexao.execute(
                "SELECT usuario_id FROM subscricoes WHERE documento_id = ? ORDER BY criada_em",
                (documento_id,),
            ).fetchall()
        return [linha["usuario_id"] for linha in linhas]

    def listar_seguidos(self, usuario_id: str) -> List[Subscricao]:
        with self._lock:
            linhas = self._conexao.execute(
                "SELECT * FROM subscricoes WHERE usuario_id = ? ORDER BY criada_em DESC",
                (usuario_id,),
            ).fetchall()
        return [
            Subscricao(
                usuario_id=l["usuario_id"], documento_id=l["documento_id"],
                criada_em=datetime.fromisoformat(l["criada_em"]),
            )
            for l in linhas
        ]

    def usuario_segue(self, usuario_id: str, documento_id: str) -> bool:
        with self._lock:
            cur = self._conexao.execute(
                "SELECT 1 FROM subscricoes WHERE usuario_id = ? AND documento_id = ?",
                (usuario_id, documento_id),
            )
            return cur.fetchone() is not None

    # --- Notificacoes ---

    def salvar_notificacao(self, notificacao: Notificacao) -> None:
        sql = """
            INSERT INTO notificacoes
                (id, usuario_id, documento_id, tipo_evento, titulo, descricao,
                 detalhes, lida, criada_em, lida_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                lida = excluded.lida,
                lida_em = excluded.lida_em
        """
        with self._lock:
            self._conexao.execute(sql, (
                notificacao.id, notificacao.usuario_id, notificacao.documento_id,
                notificacao.tipo_evento.value, notificacao.titulo, notificacao.descricao,
                json.dumps(notificacao.detalhes, ensure_ascii=False),
                1 if notificacao.lida else 0,
                notificacao.criada_em.isoformat(),
                notificacao.lida_em.isoformat() if notificacao.lida_em else None,
            ))
            self._conexao.commit()

    def obter_notificacao(self, notificacao_id: str) -> Optional[Notificacao]:
        with self._lock:
            linha = self._conexao.execute(
                "SELECT * FROM notificacoes WHERE id = ?", (notificacao_id,),
            ).fetchone()
        return self._linha_para_notificacao(linha) if linha else None

    def listar_notificacoes(
        self,
        usuario_id: str,
        lida: Optional[bool] = None,
        documento_id: Optional[str] = None,
        limite: int = 50,
    ) -> List[Notificacao]:
        clausulas = ["usuario_id = ?"]
        valores: list = [usuario_id]
        if lida is True:
            clausulas.append("lida = 1")
        elif lida is False:
            clausulas.append("lida = 0")
        if documento_id is not None:
            clausulas.append("documento_id = ?")
            valores.append(documento_id)
        sql = (
            f"SELECT * FROM notificacoes WHERE {' AND '.join(clausulas)} "
            f"ORDER BY criada_em DESC LIMIT ?"
        )
        valores.append(limite)
        with self._lock:
            linhas = self._conexao.execute(sql, valores).fetchall()
        return [self._linha_para_notificacao(l) for l in linhas]

    def contar_nao_lidas(self, usuario_id: str) -> int:
        with self._lock:
            cur = self._conexao.execute(
                "SELECT COUNT(*) FROM notificacoes WHERE usuario_id = ? AND lida = 0",
                (usuario_id,),
            )
            return cur.fetchone()[0]

    def marcar_todas_como_lidas(self, usuario_id: str) -> int:
        from datetime import timezone
        agora = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cur = self._conexao.execute(
                "UPDATE notificacoes SET lida = 1, lida_em = ? "
                "WHERE usuario_id = ? AND lida = 0",
                (agora, usuario_id),
            )
            self._conexao.commit()
            return cur.rowcount

    def fechar(self) -> None:
        with self._lock:
            self._conexao.close()

    @staticmethod
    def _linha_para_notificacao(linha: sqlite3.Row) -> Notificacao:
        return Notificacao(
            id=linha["id"],
            usuario_id=linha["usuario_id"],
            documento_id=linha["documento_id"],
            tipo_evento=TipoEventoNotificacao(linha["tipo_evento"]),
            titulo=linha["titulo"],
            descricao=linha["descricao"] or "",
            detalhes=json.loads(linha["detalhes"]) if linha["detalhes"] else {},
            lida=bool(linha["lida"]),
            criada_em=datetime.fromisoformat(linha["criada_em"]),
            lida_em=datetime.fromisoformat(linha["lida_em"]) if linha["lida_em"] else None,
        )
