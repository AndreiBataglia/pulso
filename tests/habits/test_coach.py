"""O treinador: grava os eventos e calcula o nervoso."""

import pytest

from pulso.clock import FakeClock
from pulso.habits import kinds
from pulso.habits.coach import HabitCoach
from pulso.habits.focus_cycle import Mode, Phase
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
    assert coach.answer("water_later").recorded == (kinds.WATER_SNOOZED,)
    clock.advance(10 * MIN)
    coach.tick(P)
    assert coach.answer("water_decline").recorded == (kinds.WATER_DECLINED,)
    assert coach.answer("drink").recorded == (kinds.WATER_DRUNK,)
    assert _events(coach) == [kinds.WATER_SNOOZED, kinds.WATER_DECLINED, kinds.WATER_DRUNK]
    assert coach.cups_today() == 1


def test_resposta_sem_efeito_nao_grava_nada(coach):
    assert coach.answer("water_later").recorded == ()
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


def _reach_reminder(coach, clock):
    """O foco abre sozinho na 1ª entrada e acaba 50 min depois (ociosidade 0 = mexendo)."""
    coach.tick(P, 0.0)
    clock.advance(50 * MIN)
    return coach.tick(P, 0.0)


def test_fim_do_foco_grava_o_pomodoro_do_dia(coach, clock):
    tick = _reach_reminder(coach, clock)
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
    _reach_reminder(coach, clock)
    coach.answer("break_decline")  # 2 (pausa)
    coach.answer("skip")  # pula o foco: o lembrete volta
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


# ---- o ciclo do foco (etapa 7, fatia 3) ----------------------------------------------------


def _rows(coach):
    return coach.store._conn.execute(
        "SELECT kind, category, planned_s, actual_s, excess_s FROM habit_event ORDER BY id"
    ).fetchall()


def test_pausar_agora_nao_grava_e_a_pausa_concluida_grava_o_resumo(coach, clock):
    _reach_reminder(coach, clock)
    assert coach.asking == "break"
    assert coach.answer("take_break").recorded == ()  # só começou: nada a anotar ainda
    assert coach.cycle.phase is Phase.BREAK
    clock.advance(10 * MIN)
    tick = coach.tick(P, 0.0)  # o descanso acabou e você está aqui
    assert tick.recorded == (kinds.BREAK_DONE,) and kinds.SHOW_BACK in tick.shown
    assert tick.summary.planned_s == 600
    assert _rows(coach)[-1] == (kinds.BREAK_DONE, "pause", 600, 600, 0)
    assert coach.breaks_today() == 1 and coach.pending("break") == 0


def test_prorrogar_grava_quantas_vezes_e_conta_no_placar(coach, clock):
    _reach_reminder(coach, clock)
    assert coach.answer("postpone").recorded == (kinds.BREAK_SNOOZED,)
    assert coach.postponed_today() == 1
    assert coach.pending("break") == 0  # prorrogar não pesa na pendência


def _return_from_absence(coach, clock, minutes=22):
    """10 min de foco, `minutes` fora e a pergunta "o que foi?" na tela."""
    coach.tick(P, 0.0)
    clock.advance(10 * MIN)
    coach.tick(P, 0.0)
    clock.advance(minutes * MIN)
    coach.tick(Presence.AWAY, minutes * MIN)  # o foco para no último gesto
    clock.advance(1)
    return coach.tick(P, 0.0)


def test_voltar_da_ausencia_pergunta_o_que_foi_e_avisa_a_interface(coach, clock):
    tick = _return_from_absence(coach, clock)
    assert tick.shown == (kinds.SHOW_ASK_BACK,) and coach.asking == "away"


def test_refeicao_e_gravada_como_descanso_mas_a_rede_nao_aprende_com_ela(coach, clock):
    _return_from_absence(coach, clock)
    tick = coach.answer("away_meal")
    assert tick.recorded == (kinds.BREAK_DONE,) and tick.rewarded == ()
    assert _rows(coach)[-1][:2] == (kinds.BREAK_DONE, "meal")


def test_pausa_na_volta_e_recompensada(coach, clock):
    _return_from_absence(coach, clock)
    tick = coach.answer("away_pause")
    assert tick.rewarded == (kinds.BREAK_DONE,)
    assert _rows(coach)[-1][:3] == (kinds.BREAK_DONE, "pause", 600)


def test_necessidade_nao_soma_pendencia(coach, clock):
    _return_from_absence(coach, clock)
    coach.answer("away_need")
    assert coach.pending("break") == 0 and coach.cycle.phase is Phase.FOCUS


def test_modo_casual_nao_conta_foco_mas_a_agua_continua(coach, clock):
    coach.set_mode(Mode.CASUAL)
    assert coach.cycle.phase is Phase.OFF
    clock.advance(60 * MIN)
    tick = coach.tick(P, 0.0)
    assert tick.shown == (kinds.SHOW_WATER,) and coach.pomodoros_today() == 0


def test_observacao_pausada_congela_o_ciclo(coach, clock):
    coach.tick(P, 0.0)
    clock.advance(30 * MIN)
    coach.tick(Presence.UNKNOWN, None)  # sem leitura: o foco não anda
    assert coach.cycle.remaining_s == pytest.approx(50 * MIN)


def test_refeicao_pelo_botao_nao_grava_ao_comecar_e_a_rede_nao_aprende(coach, clock):
    coach.tick(P, 0.0)  # a 1ª entrada abre o foco
    assert coach.answer("start_meal").recorded == ()
    assert coach.cycle.meal
    tick = coach.answer("end_break_early")
    assert tick.recorded == (kinds.BREAK_DONE,) and tick.rewarded == ()
    assert _rows(coach)[-1][:2] == (kinds.BREAK_DONE, "meal")
