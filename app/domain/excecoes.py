# Excecoes de dominio do Perfis-Usuarios


class AuditoriaInvalidaError(ValueError):
    """Tentativa de registrar auditoria com campos faltando ou invalidos."""
    pass


class FiltroAuditoriaInvalidoError(ValueError):
    """Combinacao de filtros invalida (ex: ate < desde)."""
    pass
