# Porta driving: SaudeService — health check do servico.

from abc import ABC, abstractmethod
from typing import Dict


class SaudeService(ABC):

    @abstractmethod
    def verificar_liveness(self) -> Dict:
        pass

    @abstractmethod
    def verificar_readiness(self) -> Dict:
        pass
