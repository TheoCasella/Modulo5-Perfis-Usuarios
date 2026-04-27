# Implementação do PapelService
# Responsabilidade: lógica de aplicação para gerenciamento de papéis.
# Depende apenas de interfaces (portas driven) — nunca de implementações.

from datetime import datetime
from typing import List

from app.application.ports.driving.papel_service import PapelService
from app.application.ports.driven.repositorio_papeis import RepositorioPapeis
from app.domain.entidades.atribuicao import Atribuicao
from app.domain.entidades.papel import NomePapel
from app.domain.excecoes import AtribuicaoDuplicadaError, AtribuicaoNaoEncontradaError


class PapelServiceImpl(PapelService):

    def __init__(self, repositorio: RepositorioPapeis):
        self._repositorio = repositorio

    def atribuir_papel(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> Atribuicao:
        ja_existe = self._repositorio.verificar_existencia(
            usuario_id, projeto_id, nome_papel
        )
        if ja_existe:
            raise AtribuicaoDuplicadaError(
                f"Usuario {usuario_id} ja tem o papel "
                f"{nome_papel.value} no projeto {projeto_id}."
            )

        atribuicao = Atribuicao( # id=0 porque o id é gerado pelo banco de dados, não pela aplicação
            id=0,
            usuario_id=usuario_id,
            projeto_id=projeto_id,
            nome_papel=nome_papel,
            criada_em=datetime.utcnow()
        )
        return self._repositorio.salvar_atribuicao(atribuicao)

    def revogar_papel(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> None:
        existe = self._repositorio.verificar_existencia(usuario_id, projeto_id, nome_papel)
        if not existe:
            raise AtribuicaoNaoEncontradaError(
                f"Atribuicao nao encontrada para usuario {usuario_id} "
                f"no projeto {projeto_id} com papel {nome_papel.value}."
            )
        self._repositorio.remover_atribuicao(usuario_id, projeto_id, nome_papel)

    def verificar_permissao(
        self,
        usuario_id: str,
        projeto_id: str,
        nome_papel: NomePapel
    ) -> bool:
        return self._repositorio.verificar_existencia(usuario_id, projeto_id, nome_papel)

    def listar_papeis_do_usuario(
        self,
        usuario_id: str,
        projeto_id: str
    ) -> List[Atribuicao]:
        return self._repositorio.listar_por_usuario_e_projeto(usuario_id, projeto_id)

    def listar_usuarios_do_projeto(
        self,
        projeto_id: str
    ) -> List[Atribuicao]:
        return self._repositorio.listar_por_projeto(projeto_id)