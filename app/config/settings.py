# Configuracoes do Perfis-Usuarios

import os

# Persistencia da auditoria.
# "memoria" = volatil (testes/dev rapido).
# "sqlite"  = persistente em arquivo local (default).
AUDITORIA_BACKEND = os.getenv("AUDITORIA_BACKEND", "sqlite")
AUDITORIA_SQLITE_PATH = os.getenv("AUDITORIA_SQLITE_PATH", "perfis_auditoria.db")
