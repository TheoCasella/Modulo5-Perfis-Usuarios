# Configuracoes do Perfis-Usuarios

import os

# Persistencia da auditoria (US PU-06).
AUDITORIA_BACKEND = os.getenv("AUDITORIA_BACKEND", "sqlite")
AUDITORIA_SQLITE_PATH = os.getenv("AUDITORIA_SQLITE_PATH", "perfis_auditoria.db")

# Persistencia de ownership (US PU-09).
OWNERSHIP_SQLITE_PATH = os.getenv("OWNERSHIP_SQLITE_PATH", "perfis_ownership.db")
# TTL do cache de ownership: enquanto for menor que isso, nao consultamos o GitHub.
OWNERSHIP_CACHE_TTL_SEGUNDOS = int(os.getenv("OWNERSHIP_CACHE_TTL_SEGUNDOS", "3600"))

# GitHub (US PU-09 / PU-02).
GITHUB_BASE_URL = os.getenv("GITHUB_BASE_URL", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # opcional; sem token bate em rate-limit anonimo
GITHUB_TIMEOUT_SEGUNDOS = float(os.getenv("GITHUB_TIMEOUT_SEGUNDOS", "5.0"))
# "github" = chamada real; "fake" = adapter local (dev offline e testes).
PROVEDOR_HISTORICO_COMMITS = os.getenv("PROVEDOR_HISTORICO_COMMITS", "github")

# Persistencia de templates de aprovacao (US PU-04).
TEMPLATES_APROVACAO_SQLITE_PATH = os.getenv(
    "TEMPLATES_APROVACAO_SQLITE_PATH", "perfis_templates.db"
)

# Persistencia de documentos em aprovacao + decisoes (US PU-05).
APROVACOES_SQLITE_PATH = os.getenv("APROVACOES_SQLITE_PATH", "perfis_aprovacoes.db")

# Persistencia de subscricoes e notificacoes (US PU-07).
NOTIFICACOES_SQLITE_PATH = os.getenv("NOTIFICACOES_SQLITE_PATH", "perfis_notificacoes.db")

# Job diario de refresh de ownership (US PU-02).
OWNERSHIP_SCHEDULER_HABILITADO = os.getenv("OWNERSHIP_SCHEDULER_HABILITADO", "true").lower() == "true"
OWNERSHIP_REFRESH_INTERVALO_HORAS = int(os.getenv("OWNERSHIP_REFRESH_INTERVALO_HORAS", "24"))
# Quantas paginas no maximo varrer no GitHub commits API (cada uma tem ate 100 commits).
OWNERSHIP_MAX_PAGINAS_GITHUB = int(os.getenv("OWNERSHIP_MAX_PAGINAS_GITHUB", "5"))
# Janela temporal opcional: se >0, considera apenas commits dos ultimos N dias.
OWNERSHIP_JANELA_DIAS = int(os.getenv("OWNERSHIP_JANELA_DIAS", "0"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
