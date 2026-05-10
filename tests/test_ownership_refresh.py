# Testes do refresh em lote e do registrar_modulo (US PU-02).

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from app.adapters.driven.clients.provedor_historico_commits_fake import (
    ProvedorHistoricoCommitsFake,
)
from app.adapters.driven.persistence.repositorio_ownership_sqlite import (
    RepositorioOwnershipSQLite,
)
from app.adapters.driven.scheduler.scheduler_diario import SchedulerDiario
from app.application.services.ownership_service_impl import OwnershipServiceImpl
from app.domain.entidades.ownership import Ownership
from app.domain.excecoes import GitHubIndisponivelError, OwnershipNaoEncontradoError


@pytest.fixture
def cenario(tmp_path):
    repo = RepositorioOwnershipSQLite(str(tmp_path / "ownership.db"))
    fake = ProvedorHistoricoCommitsFake()
    service = OwnershipServiceImpl(fake, repo, cache_ttl_segundos=3600)
    yield service, fake, repo
    repo.fechar()


# ------------- registrar_modulo -------------

def test_registrar_modulo_consulta_github_e_persiste(cenario):
    service, fake, repo = cenario
    fake.configurar("o/r", "x.py", Ownership(
        repositorio="o/r", modulo="x.py", owner_id="alice", confianca=0.9, total_commits=10,
    ))
    o = service.registrar_modulo("o/r", "x.py")
    assert o.owner_id == "alice"
    assert repo.obter("o/r", "x.py") is not None


def test_registrar_modulo_existente_retorna_sem_consultar(cenario):
    service, fake, repo = cenario
    repo.salvar(Ownership(
        repositorio="o/r", modulo="x.py", owner_id="bob", confianca=0.8, total_commits=5,
    ))
    fake.fazer_falhar_com(GitHubIndisponivelError("nao deveria chamar"))
    o = service.registrar_modulo("o/r", "x.py")
    assert o.owner_id == "bob"


def test_registrar_modulo_github_fora_cria_placeholder(cenario):
    service, fake, repo = cenario
    fake.fazer_falhar_com(GitHubIndisponivelError("503"))
    o = service.registrar_modulo("o/r", "novo.py")
    assert o.owner_id == "(desconhecido)"
    assert o.confianca == 0.0
    assert repo.obter("o/r", "novo.py") is not None


def test_registrar_modulo_sem_commits_cria_placeholder(cenario):
    service, _, repo = cenario  # fake sem configuracao -> levanta OwnershipNaoEncontradoError
    o = service.registrar_modulo("o/r", "vazio.py")
    assert o.owner_id == "(desconhecido)"
    assert repo.obter("o/r", "vazio.py") is not None


# ------------- refrescar_todos -------------

def test_refrescar_todos_atualiza_quem_mudou(cenario):
    service, fake, repo = cenario
    repo.salvar(Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.6, total_commits=3,
    ))
    repo.salvar(Ownership(
        repositorio="o/r", modulo="b.py", owner_id="bob", confianca=0.7, total_commits=4,
    ))
    # Mudanca em a.py: bob agora eh o owner
    fake.configurar("o/r", "a.py", Ownership(
        repositorio="o/r", modulo="a.py", owner_id="bob", confianca=0.9, total_commits=10,
    ))
    # b.py inalterado
    fake.configurar("o/r", "b.py", Ownership(
        repositorio="o/r", modulo="b.py", owner_id="bob", confianca=0.7, total_commits=4,
    ))

    resultado = service.refrescar_todos()
    assert resultado.total_avaliados == 2
    assert resultado.refrescados == 1
    assert resultado.sem_mudanca == 1
    assert resultado.falhas == 0
    assert repo.obter("o/r", "a.py").owner_id == "bob"


def test_refrescar_todos_conta_falhas_sem_quebrar(cenario):
    service, fake, repo = cenario
    repo.salvar(Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.5, total_commits=1,
    ))
    repo.salvar(Ownership(
        repositorio="o/r", modulo="b.py", owner_id="bob", confianca=0.5, total_commits=1,
    ))
    fake.configurar("o/r", "a.py", Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.5, total_commits=1,
    ))
    # b.py: GitHub fora — fake esta configurado para falhar globalmente?
    # Como configurar_resposta sobrescreve _falha_global, vou usar so config para a.py
    # e b.py cai no default (raise OwnershipNaoEncontradoError). Para simular falha de rede,
    # uso fazer_falhar_com — mas isso afetaria a.py tambem. Solucao: remover config e configurar
    # o fake para a.py manter, e simular falha reset depois.
    # Simplifico: faco o fake sempre devolver pra a.py e usar fila de chamadas com falha pra b.py
    # via patching do metodo:
    chamadas = []
    original = fake.identificar_owner

    def patched(repo_, modulo_):
        chamadas.append((repo_, modulo_))
        if modulo_ == "b.py":
            raise GitHubIndisponivelError("503 simulado")
        return original(repo_, modulo_)
    fake.identificar_owner = patched

    resultado = service.refrescar_todos()
    assert resultado.total_avaliados == 2
    assert resultado.falhas == 1
    assert any("b.py" in e for e in resultado.erros)
    # a.py ainda foi avaliado
    assert resultado.sem_mudanca == 1


def test_refrescar_todos_sem_dados_devolve_zero(cenario):
    service, _, _ = cenario
    resultado = service.refrescar_todos()
    assert resultado.total_avaliados == 0
    assert resultado.refrescados == 0
    assert resultado.duracao_segundos >= 0


def test_refrescar_modulo_que_perdeu_commits_nao_eh_falha(cenario):
    service, fake, repo = cenario
    repo.salvar(Ownership(
        repositorio="o/r", modulo="a.py", owner_id="alice", confianca=0.5, total_commits=1,
    ))
    # Fake nao tem config -> levanta OwnershipNaoEncontradoError
    resultado = service.refrescar_todos()
    assert resultado.falhas == 0
    assert resultado.sem_mudanca == 1


# ------------- SchedulerDiario -------------

def test_scheduler_executa_tarefa_imediatamente_se_solicitado():
    contagem = {"x": 0}
    barreira = threading.Event()

    def tarefa():
        contagem["x"] += 1
        barreira.set()

    sched = SchedulerDiario(tarefa, intervalo_segundos=3600)
    sched.iniciar(executar_imediatamente=True)
    assert barreira.wait(timeout=2.0)
    assert contagem["x"] >= 1
    sched.parar()


def test_scheduler_para_e_nao_executa_mais():
    contagem = {"x": 0}

    def tarefa():
        contagem["x"] += 1

    sched = SchedulerDiario(tarefa, intervalo_segundos=3600)
    sched.iniciar(executar_imediatamente=True)
    time.sleep(0.2)
    valor_antes = contagem["x"]
    sched.parar()
    assert sched.esta_rodando() is False
    time.sleep(0.1)
    assert contagem["x"] == valor_antes  # nao incrementou apos parar


def test_scheduler_engole_excecoes_da_tarefa():
    """Se a tarefa levantar, o scheduler nao morre — proximo ciclo tenta de novo."""
    contagem = {"x": 0}
    barreira = threading.Event()

    def tarefa():
        contagem["x"] += 1
        if contagem["x"] == 1:
            barreira.set()
            raise RuntimeError("boom")
        # segunda chamada normal

    sched = SchedulerDiario(tarefa, intervalo_segundos=3600)
    sched.iniciar(executar_imediatamente=True)
    assert barreira.wait(timeout=2.0)
    assert sched.esta_rodando() is True  # nao morreu
    sched.parar()


def test_scheduler_intervalo_invalido_falha():
    with pytest.raises(ValueError):
        SchedulerDiario(lambda: None, intervalo_segundos=0)
