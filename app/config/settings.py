# Configurações da aplicação
# Responsabilidade: centralizar variáveis de ambiente e configurações globais.
# Nenhuma outra camada deve ter strings de conexao ou segredos hardcoded.

import os

# Banco de dados
# Localmente: SQLite (arquivo local, zero configuração)
# Producao (Azure): trocar pela URL do PostgreSQL sem mexer em mais nada
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./perfis_usuarios.db"
)

# Flask
FLASK_ENV = os.getenv("FLASK_ENV", "development")
FLASK_DEBUG = FLASK_ENV == "development"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-trocar-em-producao")

# Servicos externos (preenchidos quando os outros repos estiverem no ar)
IA_ANALISE_URL = os.getenv("IA_ANALISE_URL", "http://localhost:5001")