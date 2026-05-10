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


class TemplateInvalidoError(ValueError):
    """Template de aprovacao com dados invalidos (papeis vazios, projeto faltando, etc)."""
    pass


class TemplateNaoEncontradoError(LookupError):
    """Template de aprovacao nao existe."""
    pass


class TemplateDuplicadoError(ValueError):
    """Ja existe template ativo para esse projeto+tipo_documento."""
    pass
