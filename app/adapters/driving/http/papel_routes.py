# Adaptador driving: rotas HTTP para gerenciamento de papéis
# Responsabilidade: traduzir requisições HTTP em chamadas ao PapelService.

from flask import Blueprint, request, jsonify

from app.application.ports.driving.papel_service import PapelService
from app.domain.entidades.papel import NomePapel
from app.domain.excecoes import (
    AtribuicaoDuplicadaError,
    AtribuicaoNaoEncontradaError,
    PermissaoNegadaError
)

papel_bp = Blueprint("papel", __name__, url_prefix="/api/papeis")


def criar_papel_routes(papel_service: PapelService) -> Blueprint:

    @papel_bp.post("/atribuir")
    def atribuir():
        dados = request.get_json(silent=True) or {}
        usuario_id = dados.get("usuario_id")
        projeto_id = dados.get("projeto_id")
        nome_papel = dados.get("nome_papel")

        if not usuario_id or not projeto_id or not nome_papel:
            return jsonify({"erro": "usuario_id, projeto_id e nome_papel sao obrigatorios."}), 400

        try:
            nome_papel_enum = NomePapel(nome_papel)
        except ValueError:
            valores = [p.value for p in NomePapel]
            return jsonify({"erro": f"nome_papel invalido. Valores aceitos: {valores}"}), 400

        try:
            atribuicao = papel_service.atribuir_papel(usuario_id, projeto_id, nome_papel_enum)
            return jsonify({
                "id": atribuicao.id,
                "usuario_id": atribuicao.usuario_id,
                "projeto_id": atribuicao.projeto_id,
                "nome_papel": atribuicao.nome_papel.value,
                "criada_em": atribuicao.criada_em.isoformat()
            }), 201
        except AtribuicaoDuplicadaError as e:
            return jsonify({"erro": str(e)}), 409

    @papel_bp.delete("/revogar")
    def revogar():
        dados = request.get_json(silent=True) or {}
        usuario_id = dados.get("usuario_id")
        projeto_id = dados.get("projeto_id")
        nome_papel = dados.get("nome_papel")

        if not usuario_id or not projeto_id or not nome_papel:
            return jsonify({"erro": "usuario_id, projeto_id e nome_papel sao obrigatorios."}), 400

        try:
            nome_papel_enum = NomePapel(nome_papel)
        except ValueError:
            return jsonify({"erro": "nome_papel invalido."}), 400

        try:
            papel_service.revogar_papel(usuario_id, projeto_id, nome_papel_enum)
            return jsonify({"mensagem": "Papel revogado com sucesso."}), 200
        except AtribuicaoNaoEncontradaError as e:
            return jsonify({"erro": str(e)}), 404

    @papel_bp.get("/verificar")
    def verificar():
        usuario_id = request.args.get("usuario_id")
        projeto_id = request.args.get("projeto_id")
        nome_papel = request.args.get("nome_papel")

        if not usuario_id or not projeto_id or not nome_papel:
            return jsonify({"erro": "usuario_id, projeto_id e nome_papel sao obrigatorios."}), 400

        try:
            nome_papel_enum = NomePapel(nome_papel)
        except ValueError:
            return jsonify({"erro": "nome_papel invalido."}), 400

        tem_permissao = papel_service.verificar_permissao(usuario_id, projeto_id, nome_papel_enum)
        return jsonify({"tem_permissao": tem_permissao}), 200

    @papel_bp.get("/usuario")
    def listar_por_usuario():
        usuario_id = request.args.get("usuario_id")
        projeto_id = request.args.get("projeto_id")

        if not usuario_id or not projeto_id:
            return jsonify({"erro": "usuario_id e projeto_id sao obrigatorios."}), 400

        atribuicoes = papel_service.listar_papeis_do_usuario(usuario_id, projeto_id)
        return jsonify([{
            "id": a.id,
            "usuario_id": a.usuario_id,
            "projeto_id": a.projeto_id,
            "nome_papel": a.nome_papel.value,
            "criada_em": a.criada_em.isoformat()
        } for a in atribuicoes]), 200

    @papel_bp.get("/projeto")
    def listar_por_projeto():
        projeto_id = request.args.get("projeto_id")

        if not projeto_id:
            return jsonify({"erro": "projeto_id e obrigatorio."}), 400

        atribuicoes = papel_service.listar_usuarios_do_projeto(projeto_id)
        return jsonify([{
            "id": a.id,
            "usuario_id": a.usuario_id,
            "projeto_id": a.projeto_id,
            "nome_papel": a.nome_papel.value,
            "criada_em": a.criada_em.isoformat()
        } for a in atribuicoes]), 200

    return papel_bp