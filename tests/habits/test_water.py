"""Lembrete de água e o lembrete genérico: relógio falso, sem Qt."""

import pytest

from pulso.clock import FakeClock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.water import Water

MIN = 60.0
CFG = HabitConfig()  # água 60 min, depois 10 min, ignora após 5 min


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def water(clock):
    return Water(clock, CFG)


def _until_asking(water, clock, presence=Presence.PRESENT):
    clock.advance(CFG.water_interval_min * MIN)
    return water.tick(presence)


def test_nao_pede_antes_da_hora(water, clock):
    clock.advance(59 * MIN)
    assert water.tick(Presence.PRESENT) == []
    assert not water.asking


def test_pede_agua_na_hora_e_so_uma_vez(water, clock):
    assert _until_asking(water, clock) == [kinds.SHOW_WATER]
    assert water.asking
    clock.advance(1)
    assert water.tick(Presence.PRESENT) == []  # já está na tela: não repete o aviso


def test_o_ocio_adia_o_lembrete_ate_a_volta(water, clock):
    assert _until_asking(water, clock, Presence.AWAY) == []
    clock.advance(30 * MIN)  # o dono segue longe: nada aparece
    assert water.tick(Presence.AWAY) == []
    assert not water.asking
    clock.advance(1)
    assert water.tick(Presence.PRESENT) == [kinds.SHOW_WATER]  # voltou: agora sim


def test_bebi_rearma_um_intervalo_inteiro(water, clock):
    _until_asking(water, clock)
    assert water.drink() == kinds.WATER_DRUNK
    assert not water.asking
    clock.advance(59 * MIN)
    assert water.tick(Presence.PRESENT) == []
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == [kinds.SHOW_WATER]


def test_bebi_vale_sem_lembrete_na_tela(water, clock):
    clock.advance(10 * MIN)
    assert water.drink() == kinds.WATER_DRUNK  # o botão está sempre disponível
    clock.advance(59 * MIN)
    assert water.tick(Presence.PRESENT) == []  # o relógio recomeçou do zero


def test_depois_adia_10_min(water, clock):
    _until_asking(water, clock)
    assert water.later() == kinds.WATER_SNOOZED
    assert not water.asking
    clock.advance(9 * MIN)
    assert water.tick(Presence.PRESENT) == []
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == [kinds.SHOW_WATER]


def test_recusei_rearma_o_intervalo_normal(water, clock):
    _until_asking(water, clock)
    assert water.decline() == kinds.WATER_DECLINED
    clock.advance(59 * MIN)
    assert water.tick(Presence.PRESENT) == []


def test_depois_e_recusei_sem_balao_nao_fazem_nada(water, clock):
    assert water.later() is None
    assert water.decline() is None


def test_sem_resposta_por_5_min_vira_ignorei(water, clock):
    _until_asking(water, clock)
    clock.advance(4 * MIN)
    assert water.tick(Presence.PRESENT) == []
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == [kinds.WATER_IGNORED]
    assert not water.asking
    clock.advance(9 * MIN)
    assert water.tick(Presence.PRESENT) == []
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == [kinds.SHOW_WATER]  # insiste em 10 min, não em 1 h


@pytest.mark.parametrize("presence", [Presence.AWAY, Presence.UNKNOWN])
def test_ignorei_nao_conta_com_o_dono_longe_ou_observacao_pausada(water, clock, presence):
    _until_asking(water, clock)
    clock.advance(30 * MIN)
    assert water.tick(presence) == []
    assert water.asking  # segue esperando: não dá para acusar quem pode nem ter visto


def test_ignorei_so_soma_o_tempo_com_o_dono_presente(water, clock):
    _until_asking(water, clock)
    clock.advance(3 * MIN)
    water.tick(Presence.PRESENT)  # 3 min presente
    clock.advance(20 * MIN)
    water.tick(Presence.AWAY)  # 20 min longe: não conta
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == []  # 4 min no total
    clock.advance(1 * MIN)
    assert water.tick(Presence.PRESENT) == [kinds.WATER_IGNORED]  # 5 min


def test_remaining_s_conta_ate_o_proximo_lembrete_e_e_none_se_desligado(water, clock):
    assert water.remaining_s == pytest.approx(CFG.water_interval_min * MIN)
    clock.advance(20 * MIN)
    assert water.remaining_s == pytest.approx(40 * MIN)
    water.set_enabled(False)
    assert water.remaining_s is None
