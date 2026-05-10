# Scheduler simples baseado em threading.Event (US PU-02).
# Roda uma tarefa em loop com intervalo definido. Daemon thread — encerra com o processo.
# Para producao com multiplos workers, trocar por celery-beat ou apscheduler distribuido.

import logging
import threading
from typing import Callable, Optional


_logger = logging.getLogger("perfis.scheduler")


class SchedulerDiario:

    def __init__(
        self,
        tarefa: Callable[[], None],
        intervalo_segundos: int,
        nome: str = "scheduler-diario",
    ):
        if intervalo_segundos <= 0:
            raise ValueError("intervalo_segundos deve ser > 0")
        self._tarefa = tarefa
        self._intervalo = intervalo_segundos
        self._nome = nome
        self._parar = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def iniciar(self, executar_imediatamente: bool = False) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(executar_imediatamente,),
            name=self._nome, daemon=True,
        )
        self._thread.start()
        _logger.info("Scheduler '%s' iniciado (intervalo=%ds)", self._nome, self._intervalo)

    def parar(self, timeout: float = 5.0) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        _logger.info("Scheduler '%s' parado", self._nome)

    def esta_rodando(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self, executar_imediatamente: bool) -> None:
        if executar_imediatamente:
            self._executar_seguro()
        while not self._parar.wait(self._intervalo):
            self._executar_seguro()

    def _executar_seguro(self) -> None:
        try:
            self._tarefa()
        except Exception:
            _logger.exception("Tarefa do scheduler '%s' levantou — sera tentada de novo no proximo ciclo", self._nome)
