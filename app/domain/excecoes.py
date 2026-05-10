# Excecoes de dominio do Perfis-Usuarios


class AuditoriaInvalidaError(ValueError):
    """Tentativa de registrar auditoria com campos faltando ou invalidos."""
    pass


class FiltroAuditoriaInvalidoError(ValueError):
    """Combinacao de filtros invalida (ex: ate < desde)."""
    pass


class GitHubIndisponivelError(RuntimeError):
    """GitHub nao respondeu (timeout, erro HTTP, rede). Usado para acionar fallback."""
    pass


class OwnershipNaoEncontradoError(LookupError):
    """Nao ha owner conhecido para o modulo (nem em cache, nem no GitHub)."""
    pass
