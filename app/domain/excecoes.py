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


class DocumentoNaoEncontradoError(LookupError):
    """Documento submetido nao existe."""
    pass


class DocumentoDuplicadoError(ValueError):
    """Ja existe um documento submetido com esse id."""
    pass


class DocumentoFinalizadoError(RuntimeError):
    """Documento ja esta em estado terminal (APROVADO, REJEITADO, CANCELADO)."""
    pass


class AprovacaoForaDeOrdemError(RuntimeError):
    """Tentativa de aprovar/rejeitar fora da ordem (fluxo SEQUENCIAL) ou com papel nao pendente."""
    pass


class AprovacaoDuplicadaError(RuntimeError):
    """Mesmo papel ja decidiu nesse documento."""
    pass


class NotificacaoInvalidaError(ValueError):
    """Tentativa de criar notificacao/subscricao com campos faltando ou invalidos."""
    pass


class SubscricaoDuplicadaError(ValueError):
    """Usuario ja segue esse documento."""
    pass


class NotificacaoNaoEncontradaError(LookupError):
    """Notificacao com esse id nao existe (ou nao pertence ao usuario)."""
    pass


class SugestaoOwnershipInvalidaError(ValueError):
    """Tentativa de sugerir/aprovar ownership com dados invalidos."""
    pass


class SemCandidatoOwnerError(LookupError):
    """Nao ha sinal historico suficiente para sugerir owner do documento."""
    pass


class OwnershipJaAtribuidoError(RuntimeError):
    """Documento ja tem owner atribuido — use reatribuir explicitamente."""
    pass
