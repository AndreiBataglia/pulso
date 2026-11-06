"""Pomodoro: fases, descanso longo, pausa do painel e a contagem independente da privacidade."""

import pytest

from pulso.clock import FakeClock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.pomodoro import Phase, Pomodoro

MIN = 60.0
P = Presence.PRESENT


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def pomo(clock):
    return Pomodoro(clock, HabitConfig())  # 50 / 10 / 20 a cada 4


def _finish_focus(pomo, clock):
    clock.advance(50 * MIN)
    return pomo.tick(P)


def test_comeca_parado_e_iniciar_abre_o_foco(pomo):
    assert pomo.phase is Phase.STOPPED and not pomo.running
    pomo.start()
    assert pomo.phase is Phase.FOCUS
    assert pomo.remaining_s == 50 * MIN


def test_contagem_regressiva(pomo, clock):
    pomo.start()
    clock.advance(10 * MIN)
    pomo.tick(P)
    assert pomo.remaining_s == pytest.approx(40 * MIN)


def test_fim_do_foco_grava_e_pergunta(pomo, clock):
    pomo.start()
    assert _finish_focus(pomo, clock) == [kinds.FOCUS_DONE, kinds.SHOW_BREAK]
    assert pomo.phase is Phase.ASKING and pomo.asking


def test_fiz_a_pausa_comeca_o_descanso_curto_e_depois_volta_ao_foco(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    assert pomo.rest() == kinds.BREAK_DONE
    assert pomo.phase is Phase.BREAK and pomo.remaining_s == 10 * MIN
    clock.advance(10 * MIN)
    assert pomo.tick(P) == [kinds.SHOW_BACK]  # "hora de voltar"
    assert pomo.phase is Phase.FOCUS and pomo.remaining_s == 50 * MIN


def test_descanso_longo_a_cada_4_focos(pomo, clock):
    pomo.start()
    for cycle in range(1, 5):
        _finish_focus(pomo, clock)
        pomo.rest()
        expected = 20 if cycle == 4 else 10
        assert pomo.remaining_s == expected * MIN, cycle
        clock.advance(expected * MIN)
        pomo.tick(P)
    _finish_focus(pomo, clock)  # 5º foco: o contador recomeçou
    pomo.rest()
    assert pomo.remaining_s == 10 * MIN


def test_depois_adia_a_pergunta_5_min(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    assert pomo.later() == kinds.BREAK_SNOOZED
    assert pomo.tick(P) == []
    clock.advance(5 * MIN)
    assert pomo.tick(P) == [kinds.SHOW_BREAK]


def test_recusei_volta_ao_foco_sem_descansar(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    assert pomo.decline() == kinds.BREAK_DECLINED
    assert pomo.phase is Phase.FOCUS and pomo.remaining_s == 50 * MIN


def test_sem_resposta_vira_ignorei_e_volta_ao_foco(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    clock.advance(5 * MIN)
    assert pomo.tick(P) == [kinds.BREAK_IGNORED]
    assert pomo.phase is Phase.FOCUS


def test_o_ocio_adia_a_pergunta_do_descanso(pomo, clock):
    pomo.start()
    clock.advance(50 * MIN)
    assert pomo.tick(Presence.AWAY) == [kinds.FOCUS_DONE]  # não pergunta a ninguém
    assert pomo.asking
    clock.advance(1 * MIN)
    assert pomo.tick(P) == [kinds.SHOW_BREAK]  # voltou: agora pergunta


def test_pausar_congela_a_contagem(pomo, clock):
    pomo.start()
    clock.advance(10 * MIN)
    pomo.pause()
    clock.advance(30 * MIN)
    assert pomo.tick(P) == []
    assert pomo.remaining_s == pytest.approx(40 * MIN)
    pomo.resume()
    clock.advance(40 * MIN)
    assert pomo.tick(P) == [kinds.FOCUS_DONE, kinds.SHOW_BREAK]


def test_pular_o_foco_vai_para_a_pergunta_e_pular_o_descanso_volta_ao_foco(pomo):
    pomo.start()
    assert pomo.skip() == kinds.SKIPPED
    assert pomo.asking
    pomo.rest()
    assert pomo.skip() == kinds.SKIPPED
    assert pomo.phase is Phase.FOCUS


def test_pular_na_pergunta_e_recusar(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    assert pomo.skip() == kinds.BREAK_DECLINED


def test_fiz_a_pausa_em_pleno_foco_registra_e_reinicia_o_foco(pomo, clock):
    pomo.start()
    clock.advance(30 * MIN)
    pomo.tick(P)
    assert pomo.rest() == kinds.BREAK_DONE
    assert pomo.remaining_s == 50 * MIN


def test_fiz_a_pausa_parado_so_registra_e_no_descanso_nao_registra_de_novo(pomo, clock):
    assert pomo.rest() == kinds.BREAK_DONE and pomo.phase is Phase.STOPPED
    pomo.start()
    _finish_focus(pomo, clock)
    pomo.rest()
    assert pomo.rest() is None  # já está descansando


def test_depois_e_recusei_sem_pergunta_nao_fazem_nada(pomo):
    pomo.start()
    assert pomo.later() is None and pomo.decline() is None


def test_a_contagem_corre_com_a_observacao_pausada(pomo, clock):
    """O pomodoro é independente da privacidade: sem leitura (UNKNOWN), o relógio anda igual."""
    pomo.start()
    clock.advance(50 * MIN)
    assert kinds.FOCUS_DONE in pomo.tick(Presence.UNKNOWN)


def test_parar_zera_tudo(pomo, clock):
    pomo.start()
    _finish_focus(pomo, clock)
    pomo.stop()
    assert pomo.phase is Phase.STOPPED and pomo.remaining_s == 0
    clock.advance(60 * MIN)
    assert pomo.tick(P) == []
