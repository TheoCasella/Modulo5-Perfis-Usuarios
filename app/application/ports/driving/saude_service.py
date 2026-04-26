# Porta driving: SaudeService
# Responsabilidade: descrever as operações de health check do serviço.

from abc import ABC, abstractmethod
from typing import Dict


class SaudeService(ABC):

    @abstractmethod
    def verificar_liveness(self) -> Dict:
        """
        Verifica se o servico esta no ar.
        Retorna dicionario com status, timestamp e versao.
        Nunca levanta excecao — sempre retorna algo.
        """
        pass

    @abstractmethod
    def verificar_readiness(self) -> Dict:
        """
        Verifica se o servico esta pronto para receber requisicoes.
        Checa conexao com banco e dependencias.
        Levanta excecao se alguma dependencia estiver indisponivel.
        """
        pass