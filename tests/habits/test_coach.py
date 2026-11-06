"""O treinador: grava os eventos e calcula o nervoso."""

import pytest

from pulso.clock import FakeClock
from pulso.habits import kinds
from pulso.habits.coach import HabitCoach
from pulso.habits.kinds import HabitConfig, Presence
from pulso.storage.db import HabitStore, open_db

MIN = 60.0
P = Presence.PRESENT


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def coach(clock):
    return HabitCoach(clock, HabitStore(open_db(":memory:")), HabitConfig())


def _events(coach):
    rows = coach.store._conn.execute("SELECT kind FROM habit_event ORDER BY id").fetchall()
    return [r[0] for r in rows]


def _ask_water(coach, clock):
    clock.advance(60 * MIN)
    return coach.tick(P)


def test_pedir_agua_avisa_a_interface_mas_nao_grava(coach, clock):
    tick = _ask_water(coach, clock)
    assert tick.shown == (kinds.SHOW_WATER,) and tick.recorded == ()
    assert coach.asking == "water"
    assert _events(coach) == []


def test_respostas_viram_eventos_gravados(coach, clock):
    _ask_water(coach, clock)
    assert coach.answer("water_later") == kinds.WATER_SNOOZED
    clock.advance(10 * MIN)
    coach.tick(P)
    assert coach.answer("water_decline") == kinds.WATER_DECLINED
    assert coach.answer("drink") == kinds.WATER_DRUNK
    assert _events(coach) == [kinds.WATER_SNOOZED, kinds.WATER_DECLINED, kinds.WATER_DRUNK]
    assert coach.cups_today() == 1


def test_resposta_sem_efeito_nao_grava_nada(coach):
    assert coach.answer("water_later") is None
    assert _events(coach) == []


def test_resposta_desconhecida_e_erro(coach):
    with pytest.raises(ValueError):
        coach.answer("apagar_tudo")


def test_omissao_e_gravada_pelo_relogio(coach, clock):
    _ask_water(coach, clock)
    clock.advance(5 * MIN)
    tick = coach.tick(P)
    assert tick.recorded == (kinds.WATER_IGNORED,)
    assert _events(coach) == [kinds.WATER_IGNORED]


def test_fim_do_foco_grava_o_pomodoro_do_dia(coach, clock):
    coach.pomodoro.start()
    clock.advance(50 * MIN)
    tick = coach.tick(P)
    assert kinds.FOCUS_DONE in tick.recorded and kinds.SHOW_BREAK in tick.shown
    assert coach.pomodoros_today() == 1
    assert coach.asking == "break"


def test_nervoso_com_3_pontos_de_pendencia(coach, clock):
    assert not coach.nervous
    _ask_water(coach, clock)
    coach.answer("water_decline")  # 2 pontos
    assert not coach.nervous
    clock.advance(60 * MIN)
    coach.tick(P)
    clock.advance(5 * MIN)
    coach.tick(P)  # ignorei: +1 = 3
    assert coach.nervous and coach.nervous_reason == "água"


def test_so_o_fiz_acalma_o_pet(coach, clock):
    _ask_water(coach, clock)
    coach.answer("water_decline")
    clock.advance(60 * MIN)
    coach.tick(P)
    coach.answer("water_decline")  # 4 pontos
    assert coach.nervous
    clock.advance(24 * 60 * MIN)  # um dia depois: continua nervoso
    assert coach.nervous
    coach.answer("drink")
    assert not coach.nervous


def test_nervoso_diz_qual_habito_esta_pendente(coach, clock):
    coach.pomodoro.start()
    clock.advance(50 * MIN)
    coach.tick(P)
    coach.answer("break_decline")  # 2 (pausa)
    coach.pomodoro.skip()
    coach.answer("break_decline")  # 4
    assert coach.nervous_reason == "pausa"


def test_pendencia_volta_depois_de_reabrir_o_app(tmp_path, clock):
    path = tmp_path / "pulso.db"
    first = HabitCoach(clock, HabitStore(open_db(path)))
    _ask_water(first, clock)
    first.answer("water_decline")
    clock.advance(60 * MIN)
    first.tick(P)
    first.answer("water_decline")
    first.store.close()
    reopened = HabitCoach(clock, HabitStore(open_db(path)))
    assert reopened.nervous
    reopened.store.close()
