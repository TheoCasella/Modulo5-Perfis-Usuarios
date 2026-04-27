# Adaptador driving: rotas HTTP de health check
# Responsabilidade: expor liveness e readiness do servico.

from flask import Blueprint, jsonify

from app.application.ports.driving.saude_service import SaudeService

saude_bp = Blueprint("saude", __name__, url_prefix="")


def criar_saude_routes(saude_service: SaudeService) -> Blueprint:

    @saude_bp.get("/health")
    def liveness():
        resultado = saude_service.verificar_liveness()
        return jsonify(resultado), 200

    @saude_bp.get("/health/ready")
    def readiness():
        try:
            resultado = saude_service.verificar_readiness()
            return jsonify(resultado), 200
        except RuntimeError as e:
            return jsonify({"status": "unavailable", "erro": str(e)}), 503

    return saude_bp