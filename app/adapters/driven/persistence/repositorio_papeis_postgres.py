# Adaptador driven: persistência de papéis com SQLAlchemy
# Implementa RepositorioPapeis usando SQLAlchemy (SQLite local / Postgres quando for para deploy).
# Responsabilidade: traduzir entre o modelo de domínio (Atribuicao) e o modelo de persistência (AtribuicaoModel).

from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Session

from app.application.ports.driven.repositorio_papeis import RepositorioPapeis
from app.domain.entidades.atribuicao import Atribuicao
from app.domain.entidades.papel import NomePapel
from app.domain.excecoes import AtribuicaoDuplicadaError, AtribuicaoNaoEncontradaError


class Base(DeclarativeBase):
    pass


class AtribuicaoModel(Base):
    __tablename__ = "atribuicoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(String, nullable=False)
    projeto_id = Column(String, nullable=False)
    nome_papel = Column(SAEnum(NomePapel), nullable=False)
    criada_em = Column(DateTime, nullable=False)


class RepositorioPapeisImpl(RepositorioPapeis):

    def __init__(self, database_url: str):
        self._engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self._engine)

    def _to_domain(self, model: AtribuicaoModel) -> Atribuicao:
        return Atribuicao(
            id=model.id,
            usuario_id=model.usuario_id,
            projeto_id=model.projeto_id,
            nome_papel=model.nome_papel,
            criada_em=model.criada_em
        )

    def salvar_atribuicao(self, atribuicao: Atribuicao) -> Atribuicao:
        with Session(self._engine) as session:
            existe = session.query(AtribuicaoModel).filter_by(
                usuario_id=atribuicao.usuario_id,
                projeto_id=atribuicao.projeto_id,
                nome_papel=atribuicao.nome_papel
            ).first()
            if existe:
                raise AtribuicaoDuplicadaError()

            model = AtribuicaoModel(
                usuario_id=atribuicao.usuario_id,
                projeto_id=atribuicao.projeto_id,
                nome_papel=atribuicao.nome_papel,
                criada_em=atribuicao.criada_em or datetime.utcnow()
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def remover_atribuicao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> None:
        with Session(self._engine) as session:
            model = session.query(AtribuicaoModel).filter_by(
                usuario_id=usuario_id,
                projeto_id=projeto_id,
                nome_papel=nome_papel
            ).first()
            if not model:
                raise AtribuicaoNaoEncontradaError()
            session.delete(model)
            session.commit()

    def buscar_atribuicao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> Optional[Atribuicao]:
        with Session(self._engine) as session:
            model = session.query(AtribuicaoModel).filter_by(
                usuario_id=usuario_id,
                projeto_id=projeto_id,
                nome_papel=nome_papel
            ).first()
            return self._to_domain(model) if model else None

    def listar_por_usuario_e_projeto(
        self,
        usuario_id: str,
        projeto_id: str
    ) -> List[Atribuicao]:
        with Session(self._engine) as session:
            modelos = session.query(AtribuicaoModel).filter_by(
                usuario_id=usuario_id,
                projeto_id=projeto_id
            ).all()
            return [self._to_domain(m) for m in modelos]

    def listar_por_projeto(
        self,
        projeto_id: str
    ) -> List[Atribuicao]:
        with Session(self._engine) as session:
            modelos = session.query(AtribuicaoModel).filter_by(
                projeto_id=projeto_id
            ).all()
            return [self._to_domain(m) for m in modelos]

    def verificar_existencia(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> bool:
        with Session(self._engine) as session:
            return session.query(AtribuicaoModel).filter_by(
                usuario_id=usuario_id,
                projeto_id=projeto_id,
                nome_papel=nome_papel
            ).first() is not None