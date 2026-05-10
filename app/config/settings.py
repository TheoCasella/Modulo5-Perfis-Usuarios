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

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
