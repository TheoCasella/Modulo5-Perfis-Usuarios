# Responsabilidade: único lugar que conhece implementações concretas.
# Monta o grafo de dependências e injeta nas camadas corretas.

from flask import Flask

from app.config.settings import DATABASE_URL
from app.adapters.driven.persistence.repositorio_papeis_postgres import RepositorioPapeisImpl
from app.application.services.papel_service_impl import PapelServiceImpl
from app.application.services.saude_service_impl import SaudeServiceImpl
from app.adapters.driving.http.papel_routes import criar_papel_routes
from app.adapters.driving.http.saude_routes import criar_saude_routes


def create_app() -> Flask:
    app = Flask(__name__)

    # Adaptadores driven (persistência)
    repositorio_papeis = RepositorioPapeisImpl(DATABASE_URL)

    # Services (Use Cases)
    papel_service = PapelServiceImpl(repositorio_papeis)
    saude_service = SaudeServiceImpl(repositorio_papeis)

    # Adaptadores driving (rotas HTTP)
    app.register_blueprint(criar_papel_routes(papel_service))
    app.register_blueprint(criar_saude_routes(saude_service))

    return app