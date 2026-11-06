"""Hábitos no controlador: recompensas, presença vinda do sensor e independência da privacidade."""

import dataclasses

import pytest

from pulso.habits import kinds
from pulso.habits.pomodoro import Phase
from tests.test_controller import FRAME, parts  # noqa: F401 (fixture `parts`)

MIN = 60.0


def _reaches_water_prompt(controller, clock):
    clock.advance(60 * MIN)
    controller.tick()
    return controller.tick_habits()


def test_bebi_recompensa_positivo_com_peso_do_dono(parts):  # noqa: F811
    controller, _, engine, _, _ = parts
    assert controller.answer_habit("drink") == kinds.WATER_DRUNK
    assert engine.rewards == [pytest.approx(1.0)]
    assert controller.dopamine_events[-1].source == "regra"


def test_recusei_e_ignorei_punem_e_depois_nao_vale_nada(parts):  # noqa: F811
    controller, _, engine, clock, _ = parts
    _reaches_water_prompt(controller, clock)
    controller.answer_habit("water_later")  # depois: 0
    assert engine.rewards == []
    clock.advance(10 * MIN)
    controller.tick()
    controller.tick_habits()  # o lembrete volta
    controller.answer_habit("water_decline")  # −1 × 1,0
    assert engine.rewards == [pytest.approx(-1.0)]
    clock.advance(60 * MIN)
    controller.tick()
    controller.tick_habits()
    clock.advance(5 * MIN)
    controller.tick()
    controller.tick_habits()  # ignorei: −0,5 × 1,0
    assert engine.rewards == [pytest.approx(-1.0), pytest.approx(-0.5)]


def test_pausado_o_evento_e_anotado_mas_a_rede_nao_aprende(parts):  # noqa: F811
    controller, _, engine, _, _ = parts
    controller.pause()
    controller.answer_habit("drink")
    assert engine.rewards == []
    assert controller.habits.cups_today() == 1  # o copo conta mesmo assim


def test_pomodoro_corre_com_a_observacao_pausada_e_nao_a_religa(parts):  # noqa: F811
    controller, sensor, _, clock, _ = parts
    controller.tick()
    controller.pause()
    calls = sensor.calls
    controller.habits.pomodoro.start()
    clock.advance(50 * MIN)
    assert controller.tick() is None
    tick = controller.tick_habits()
    assert kinds.FOCUS_DONE in tick.recorded
    assert controller.paused  # o pomodoro não religou a observação...
    assert sensor.calls == calls  # ...nem leu o sensor


def test_pausar_e_retomar_nao_mexem_no_pomodoro(parts):  # noqa: F811
    controller, _, _, clock, _ = parts
    controller.tick()
    controller.habits.pomodoro.start()
    clock.advance(10 * MIN)
    controller.pause()
    controller.resume()
    controller.tick()
    controller.tick_habits()
    pomo = controller.habits.pomodoro
    assert pomo.phase is Phase.FOCUS and pomo.remaining_s == pytest.approx(40 * MIN)


def test_dono_longe_segura_o_lembrete_de_agua(parts):  # noqa: F811
    controller, sensor, _, clock, _ = parts
    idle = dataclasses.replace(FRAME, idle_seconds=10 * MIN)
    sensor._script = [idle]
    clock.advance(60 * MIN)
    assert controller.tick() is not None
    assert controller.tick_habits().shown == ()
    assert not controller.habits.water.asking


def test_nervoso_vence_o_humor_da_rede_ate_o_dono_dizer_que_fez(parts):  # noqa: F811
    controller, _, _, clock, _ = parts
    for _ in range(10):  # a rede já decidiu um humor
        controller.tick()
        clock.advance(1)
    assert controller.shown_mood == controller.mood
    _reaches_water_prompt(controller, clock)
    controller.answer_habit("water_decline")  # 2
    clock.advance(60 * MIN)
    controller.tick()
    controller.tick_habits()
    controller.answer_habit("water_decline")  # 4
    assert controller.shown_mood == "nervoso"
    assert controller.mood != "nervoso"  # a rede segue decidindo; só o rosto é vencido
    controller.answer_habit("drink")
    assert controller.shown_mood == controller.mood
