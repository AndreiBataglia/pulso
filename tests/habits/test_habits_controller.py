"""Hábitos no controlador: recompensas, presença vinda do sensor e independência da privacidade."""

import dataclasses

import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.controller import PetController
from pulso.habits import kinds
from pulso.habits.focus_cycle import Mode, Phase
from pulso.sensors.meeting import FakeMeetingSensor
from pulso.storage.brain_store import AutoSaver
from tests.test_controller import FRAME, make_habits, parts  # noqa: F401, F811

MIN = 60.0


def _reaches_water_prompt(controller, clock):
    clock.advance(60 * MIN)
    controller.tick()
    return controller.tick_habits()


def test_bebi_recompensa_positivo_com_peso_do_dono(parts):  # noqa: F811
    controller, _, engine, _, _ = parts
    assert controller.answer_habit("drink").recorded == (kinds.WATER_DRUNK,)
    assert engine.rewards == [pytest.approx(1.0)]
    assert controller.dopamine_events[-1].source == "regra"


def test_recusei_e_ignorei_punem_e_depois_nao_vale_nada(parts):  # noqa: F811
    controller, _, engine, clock, _ = parts
    controller.set_mode(Mode.CASUAL)  # sem ciclo do foco: aqui só interessa a água
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


def test_o_ciclo_congela_com_a_observacao_pausada_e_nao_a_religa(parts):  # noqa: F811
    controller, sensor, _, clock, _ = parts
    controller.tick()
    controller.tick_habits()  # a 1ª entrada abre o foco sozinha
    assert controller.habits.cycle.phase is Phase.FOCUS
    controller.pause()
    calls = sensor.calls
    clock.advance(50 * MIN)
    assert controller.tick() is None
    tick = controller.tick_habits()
    assert tick.recorded == ()  # sem leitura não há presença: o foco não anda
    assert controller.habits.cycle.remaining_s == pytest.approx(50 * MIN)
    assert controller.paused  # nada religou a observação...
    assert sensor.calls == calls  # ...nem leu o sensor


def test_pausar_e_retomar_nao_mexem_no_foco(parts):  # noqa: F811
    controller, _, _, clock, _ = parts
    controller.tick()
    controller.tick_habits()
    clock.advance(10 * MIN)
    controller.tick()
    controller.tick_habits()
    controller.pause()
    controller.resume()
    controller.tick()
    controller.tick_habits()
    cycle = controller.habits.cycle
    assert cycle.phase is Phase.FOCUS and cycle.remaining_s == pytest.approx(40 * MIN)


def _with_meeting(parts, script):  # noqa: F811
    _, sensor, engine, clock, path = parts
    meeting = FakeMeetingSensor(script)
    other = PetController(
        sensor, clock, engine, MoodDecoder(engine.groups), RewardRules(clock),
        AutoSaver(engine, path, 1, clock), make_habits(clock), meeting,
    )  # fmt: skip
    return other, meeting, clock


def test_microfone_em_uso_pausa_o_foco_sem_penalizar(parts):  # noqa: F811
    controller, _, clock = _with_meeting(parts, [False, True])
    controller.tick()
    controller.tick_habits()
    assert controller.habits.cycle.phase is Phase.FOCUS
    clock.advance(25 * MIN)
    controller.tick()
    controller.tick_habits()  # o microfone passou a "em uso"
    assert controller.habits.cycle.phase is Phase.MEETING
    clock.advance(60 * MIN)
    controller.tick()
    tick = controller.tick_habits()
    assert tick.recorded == () and controller.habits.pending("break") == 0


def test_com_a_observacao_pausada_o_sensor_de_reuniao_nem_e_lido(parts):  # noqa: F811
    controller, meeting, _ = _with_meeting(parts, [True])
    controller.pause()
    controller.tick()
    controller.tick_habits()
    assert meeting.calls == 0


def test_pausar_agora_nao_grava_nem_recompensa(parts):  # noqa: F811
    controller, _, engine, _, _ = parts
    controller.tick()
    controller.tick_habits()
    tick = controller.answer_habit("take_break")
    assert tick.recorded == () and engine.rewards == []
    assert controller.habits.cycle.phase is Phase.BREAK


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
