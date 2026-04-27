# Exceções de domínio do serviço Perfis-Usuarios
# Responsabilidade: sinalizar violações de regras de negócio.
# Não usar exceções genéricas do Python para erros de domínio.
# Essa especificidade é o que permite que a camada de adaptadores HTTP traduza erros de domínio em status HTTP corretos sem lógica condicional complexa.

class PapelNaoEncontradoError(Exception):
    """Lancada quando um papel requisitado nao existe."""
    pass


class AtribuicaoNaoEncontradaError(Exception):
    """Lancada quando uma atribuicao requisitada nao existe."""
    pass


class PermissaoNegadaError(Exception):
    """Lancada quando usuario nao tem papel suficiente para a acao."""
    pass


class AtribuicaoDuplicadaError(Exception):
    """Lancada quando usuario ja tem o papel no projeto."""
    pass


class UsuarioNaoEncontradoError(Exception):
    """Lancada quando usuario requisitado nao existe."""
    pass


class ProjetoNaoEncontradoError(Exception):
    """Lancada quando projeto requisitado nao existe."""
    pass