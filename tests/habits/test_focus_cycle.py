"""Ciclo do foco por presença: roteiros com relógio falso (nenhum sensor, nenhum clique)."""

import pytest

from pulso.clock import FakeClock
from pulso.habits import kinds
from pulso.habits.focus_cycle import (
    AwayAnswer,
    CycleEvent,
    FocusCycle,
    Mode,
    Phase,
)
from pulso.habits.kinds import HabitConfig

MIN = 60.0
ACTIVE = 0.0  # ociosidade de quem está mexendo agora


@pytest.fixture
def clock():
    return FakeClock(start=1000.0)


@pytest.fixture
def cycle(clock):
    return FocusCycle(clock, HabitConfig())  # 50 / 10 / 20 a cada 4, tolerância 5 min


def kinds_of(events):
    return [e.kind for e in events]


def work(cycle, clock, minutes, step=1.0):
    """Trabalha `minutes` mexendo no PC; devolve os acontecimentos."""
    events = []
    for _ in range(int(minutes * MIN / step)):
        clock.advance(step)
        events += cycle.tick(ACTIVE)
    return events


def idle_for(cycle, clock, seconds, meeting=False):
    """Fica `seconds` sem mexer (a ociosidade do sensor cresce a cada segundo)."""
    events = []
    for sec in range(1, int(seconds) + 1):
        clock.advance(1)
        events += cycle.tick(float(sec), meeting)
    return events


def reach_reminder(cycle, clock):
    cycle.tick(ACTIVE)  # 1ª entrada
    return work(cycle, clock, 50)


# ---- começa sozinho ------------------------------------------------------------------------


def test_comeca_aguardando_e_a_primeira_entrada_abre_o_foco_sem_clicar_em_nada(cycle):
    assert cycle.phase is Phase.WAITING
    assert cycle.tick(120.0) == [] and cycle.phase is Phase.WAITING  # ninguém mexeu
    cycle.tick(ACTIVE)
    assert cycle.phase is Phase.FOCUS and cycle.remaining_s == 50 * MIN


def test_o_foco_corre_com_o_relogio_enquanto_se_trabalha(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    assert cycle.remaining_s == pytest.approx(40 * MIN)


def test_fim_do_foco_grava_conta_o_ciclo_e_chama_o_lembrete(cycle, clock):
    events = reach_reminder(cycle, clock)
    assert kinds_of(events) == [kinds.FOCUS_DONE, kinds.SHOW_BREAK]
    assert cycle.phase is Phase.REMINDER


# ---- tolerância e ausência -----------------------------------------------------------------


def test_parado_menos_que_a_tolerancia_ainda_e_foco(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    idle_for(cycle, clock, 4 * MIN)  # pensou 4 min olhando a tela
    assert cycle.phase is Phase.FOCUS


def test_passou_da_tolerancia_o_foco_para_no_ultimo_gesto(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    idle_for(cycle, clock, 6 * MIN)
    assert cycle.phase is Phase.AWAY
    # 10 min de trabalho de verdade; os 5 min parados antes da detecção não contam
    assert cycle.remaining_s == pytest.approx(40 * MIN, abs=2)


def test_voltar_de_uma_ausencia_pergunta_o_que_foi_com_o_tempo_fora(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    idle_for(cycle, clock, 22 * MIN)
    clock.advance(1)
    assert kinds_of(cycle.tick(ACTIVE)) == [kinds.SHOW_ASK_BACK]
    assert cycle.phase is Phase.ASKING_BACK
    assert cycle.last_absence_s == pytest.approx(22 * MIN + 1, abs=2)


@pytest.fixture
def asking(cycle, clock):
    """Dez minutos de foco, 22 min fora e a pergunta na tela."""
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    idle_for(cycle, clock, 22 * MIN)
    clock.advance(1)
    cycle.tick(ACTIVE)
    return cycle


def test_resposta_pausa_conta_a_pausa_com_o_excesso_e_recomeca_o_foco(asking):
    (event,) = asking.answer_back(AwayAnswer.PAUSE)
    assert event.kind == kinds.BREAK_DONE and event.category == "pause"
    assert event.planned_s == 10 * 60 and event.actual_s == pytest.approx(22 * 60, abs=2)
    assert event.excess_s == pytest.approx(12 * 60, abs=2)  # "+12 min além dos 10"
    assert asking.phase is Phase.FOCUS and asking.remaining_s == 50 * MIN


def test_resposta_refeicao_e_descanso_longo_sem_excesso(asking):
    (event,) = asking.answer_back(AwayAnswer.MEAL)
    assert event.kind == kinds.BREAK_DONE and event.category == "meal"
    assert event.planned_s == 20 * 60 and event.excess_s == 0
    assert asking.phase is Phase.FOCUS and asking.remaining_s == 50 * MIN


def test_resposta_necessidade_nao_conta_pausa_nem_penaliza_e_o_foco_continua(asking):
    (event,) = asking.answer_back(AwayAnswer.NEED)
    assert event.kind == kinds.AWAY_NEED and event.category == "need"
    assert asking.phase is Phase.FOCUS and asking.remaining_s == pytest.approx(40 * MIN, abs=2)


def test_resposta_foco_sem_mexer_transforma_o_tempo_fora_em_foco(asking):
    (event,) = asking.answer_back(AwayAnswer.FOCUS)
    assert event.kind == kinds.AWAY_FOCUS and event.category == "focus"
    assert asking.remaining_s == pytest.approx(18 * MIN, abs=3)  # 10 + 22 min já feitos


def test_sem_resposta_conta_como_pausa(asking, clock):
    events = []
    for _ in range(121):
        clock.advance(1)
        events += asking.tick(ACTIVE)
    assert [e.kind for e in events] == [kinds.BREAK_DONE]
    assert events[0].category == "pause" and asking.phase is Phase.FOCUS


def test_a_pergunta_sem_resposta_nao_conta_o_tempo_com_voce_longe(asking, clock):
    for sec in range(1, 10 * 60):  # saiu de novo com a pergunta na tela
        clock.advance(1)
        assert asking.tick(400.0 + sec) == []
    assert asking.phase is Phase.ASKING_BACK


# ---- lembrete e as respostas ---------------------------------------------------------------


def test_prorrogar_volta_ao_foco_por_5_min_sem_limite_e_conta_as_vezes(cycle, clock):
    reach_reminder(cycle, clock)
    (event,) = cycle.postpone()
    assert event.kind == kinds.BREAK_SNOOZED and cycle.phase is Phase.FOCUS
    assert cycle.remaining_s == pytest.approx(5 * MIN)
    events = work(cycle, clock, 5)
    assert kinds_of(events) == [kinds.SHOW_BREAK]  # FOCUS_DONE não repete ao prorrogar
    cycle.postpone()
    work(cycle, clock, 5)
    cycle.postpone()
    assert cycle.postponements == 3 and cycle.phase is Phase.FOCUS


def test_pausa_depois_de_prorrogar_grava_quantas_vezes_foi_adiada(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.postpone()
    work(cycle, clock, 5)
    cycle.take_break()
    events = work(cycle, clock, 10)
    assert events[0].kind == kinds.BREAK_DONE and events[0].value == 1


def test_hoje_nao_grava_a_recusa_e_comeca_um_foco_novo(cycle, clock):
    reach_reminder(cycle, clock)
    assert kinds_of(cycle.decline()) == [kinds.BREAK_DECLINED]
    assert cycle.phase is Phase.FOCUS and cycle.remaining_s == 50 * MIN


def test_pausar_agora_comeca_o_descanso_de_10_min(cycle, clock):
    reach_reminder(cycle, clock)
    assert cycle.take_break()
    assert cycle.phase is Phase.BREAK and cycle.remaining_s == 10 * MIN


def test_sem_resposta_o_lembrete_vira_ignorei_e_o_foco_recomeca(cycle, clock):
    reach_reminder(cycle, clock)
    events = work(cycle, clock, 5)
    assert kinds_of(events) == [kinds.BREAK_IGNORED]
    assert cycle.phase is Phase.FOCUS


def test_sair_da_mesa_durante_o_lembrete_vale_como_pausa_aceita_contada_do_ultimo_gesto(
    cycle, clock
):
    reach_reminder(cycle, clock)
    idle_for(cycle, clock, 2 * MIN)  # ouviu o aviso e levantou
    assert cycle.phase is Phase.BREAK
    assert cycle.remaining_s == pytest.approx(8 * MIN, abs=1.5)  # já passaram 2 dos 10 min


# ---- descanso ------------------------------------------------------------------------------


def test_mexer_no_pc_durante_o_descanso_nao_o_encerra(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    work(cycle, clock, 5)  # olhou o celular, mexeu no mouse
    assert cycle.phase is Phase.BREAK and cycle.remaining_s == pytest.approx(5 * MIN)


def test_fim_do_descanso_com_voce_aqui_grava_e_volta_ao_foco(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    events = work(cycle, clock, 10)
    assert kinds_of(events) == [kinds.BREAK_DONE, kinds.SHOW_BACK]
    done = events[0]
    assert done.category == "pause" and done.planned_s == 600 and done.excess_s == 0
    assert cycle.phase is Phase.FOCUS and cycle.remaining_s == 50 * MIN


def test_descanso_que_passa_do_tempo_conta_o_excesso_e_o_foco_volta_na_primeira_entrada(
    cycle, clock
):
    reach_reminder(cycle, clock)
    cycle.take_break()
    events = idle_for(cycle, clock, 16 * MIN)  # 10 min de pausa + 6 além, ainda fora
    assert events == [] and cycle.phase is Phase.BREAK_OVER
    clock.advance(1)
    events = cycle.tick(ACTIVE)
    assert kinds_of(events) == [kinds.BREAK_DONE, kinds.SHOW_BACK]
    assert events[0].excess_s == pytest.approx(6 * 60, abs=3)  # "10 min + 6 além"
    assert events[0].actual_s == pytest.approx(16 * 60, abs=3)
    assert cycle.phase is Phase.FOCUS


def test_voltar_ao_foco_antes_conta_a_pausa_pela_metade(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    work(cycle, clock, 4)
    (event,) = cycle.end_break_early()
    assert event.kind == kinds.BREAK_DONE and event.actual_s == pytest.approx(240, abs=1)
    assert cycle.phase is Phase.FOCUS


def test_descanso_longo_a_cada_4_focos(cycle, clock):
    cycle.tick(ACTIVE)
    for number in range(1, 5):
        work(cycle, clock, 50)
        cycle.take_break()
        expected = 20 if number == 4 else 10
        assert cycle.remaining_s == expected * MIN, number
        work(cycle, clock, expected)
    work(cycle, clock, 50)  # 5º foco: o contador recomeçou
    cycle.take_break()
    assert cycle.remaining_s == 10 * MIN


# ---- reunião -------------------------------------------------------------------------------


def test_reuniao_congela_o_foco_sem_perguntar_nada_na_volta(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    events = idle_for(cycle, clock, 60 * MIN, meeting=True)  # 1 h de call, sem mexer
    assert events == [] and cycle.phase is Phase.MEETING
    clock.advance(1)
    assert cycle.tick(3601.0, meeting=False) == []  # a call acabou; ociosidade herdada da call
    assert cycle.phase is Phase.FOCUS
    assert cycle.remaining_s == pytest.approx(40 * MIN, abs=2)  # o foco parou, não zerou


def test_depois_da_reuniao_so_conta_ausencia_a_partir_do_fim_dela(cycle, clock):
    cycle.tick(ACTIVE)
    idle_for(cycle, clock, 30 * MIN, meeting=True)
    clock.advance(1)
    cycle.tick(1800.0)  # fim da reunião
    for _ in range(60):
        clock.advance(1)
        cycle.tick(1800.0 + 60)  # o sensor ainda diz "parado há 30 min"
    assert cycle.phase is Phase.FOCUS


def test_reuniao_durante_a_ausencia_cancela_a_pergunta(cycle, clock):
    cycle.tick(ACTIVE)
    idle_for(cycle, clock, 7 * MIN)
    assert cycle.phase is Phase.AWAY
    clock.advance(1)
    cycle.tick(421.0, meeting=True)
    assert cycle.phase is Phase.MEETING


def test_reuniao_nao_interrompe_o_descanso(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    clock.advance(1)
    cycle.tick(ACTIVE, meeting=True)
    assert cycle.phase is Phase.BREAK


# ---- observação pausada e modo casual ------------------------------------------------------


def test_observacao_pausada_congela_tudo_incluindo_a_presenca(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    for _ in range(30 * 60):
        clock.advance(1)
        assert cycle.tick(None) == []  # escudo ligado: sem leitura
    assert cycle.phase is Phase.FOCUS and cycle.remaining_s == pytest.approx(40 * MIN)


def test_modo_casual_desliga_o_ciclo(clock):
    cycle = FocusCycle(clock, HabitConfig(), mode=Mode.CASUAL)
    assert cycle.phase is Phase.OFF
    for _ in range(120 * 60):
        clock.advance(1)
        assert cycle.tick(ACTIVE) == []  # nunca conta foco nem chama para pausa
    assert cycle.phase is Phase.OFF


def test_trocar_o_modo_liga_e_desliga_o_ciclo(cycle, clock):
    cycle.tick(ACTIVE)
    work(cycle, clock, 10)
    cycle.set_mode(Mode.CASUAL)
    assert cycle.phase is Phase.OFF
    cycle.set_mode(Mode.PROFESSIONAL)
    assert cycle.phase is Phase.WAITING  # recomeça: a próxima entrada abre o foco
    cycle.tick(ACTIVE)
    assert cycle.remaining_s == 50 * MIN


# ---- pular fase ----------------------------------------------------------------------------


def test_pular_o_foco_vai_ao_lembrete_sem_contar_foco_concluido(cycle, clock):
    cycle.tick(ACTIVE)
    assert kinds_of(cycle.skip()) == [kinds.SKIPPED, kinds.SHOW_BREAK]
    assert cycle.phase is Phase.REMINDER
    cycle.take_break()
    assert cycle.skip() == [CycleEvent(kinds.SKIPPED)] and cycle.phase is Phase.FOCUS


# ---- o que a janela lê (etapa 7, fatia 3) -------------------------------------------------


def test_andamento_numero_do_foco_e_pausa_prevista(cycle, clock):
    assert cycle.progress == 0.0 and cycle.focus_total == 4
    cycle.tick(ACTIVE)
    work(cycle, clock, 25)
    assert cycle.progress == pytest.approx(0.5, abs=0.01)
    assert cycle.focus_number == 1 and cycle.worked_s == pytest.approx(25 * MIN)
    assert cycle.planned_break_s == 10 * MIN
    work(cycle, clock, 25)
    assert cycle.phase is Phase.REMINDER and cycle.progress == 1.0  # lembrete: anel cheio


def test_o_numero_do_foco_avanca_depois_de_cada_foco_concluido(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    work(cycle, clock, 10)
    work(cycle, clock, 1)
    assert cycle.phase is Phase.FOCUS and cycle.focus_number == 2


def test_o_andamento_do_descanso_chega_a_1_e_depois_fica_cheio(cycle, clock):
    reach_reminder(cycle, clock)
    cycle.take_break()
    work(cycle, clock, 5)
    assert cycle.progress == pytest.approx(0.5, abs=0.01)
    idle_for(cycle, clock, 5 * MIN)
    assert cycle.progress == 1.0


# ---- botão Refeição (ao lado do modo) -------------------------------------------------------


def test_refeicao_anunciada_comeca_descanso_longo_e_grava_como_refeicao(cycle, clock):
    cycle.tick(ACTIVE)  # abre o foco
    assert cycle.start_meal() and cycle.phase is Phase.BREAK
    assert cycle.meal and cycle.long_break and cycle.remaining_s == 20 * MIN
    events = []
    for _ in range(int(20 * MIN) + 1):  # o descanso acaba e o dono mexe no PC
        clock.advance(1)
        events += cycle.tick(ACTIVE)
    done = [e for e in events if e.kind == kinds.BREAK_DONE]
    assert len(done) == 1 and done[0].category == kinds.CAT_MEAL
    assert done[0].planned_s == 20 * MIN and done[0].excess_s == 0
    assert cycle.phase is Phase.FOCUS and not cycle.meal and cycle.focus_number == 1


def test_refeicao_que_passa_do_tempo_nao_tem_excesso(cycle, clock):
    cycle.tick(ACTIVE)
    cycle.start_meal()
    events = idle_for(cycle, clock, 25 * MIN)  # ainda longe depois dos 20 min
    assert cycle.phase is Phase.BREAK_OVER and events == []
    clock.advance(1)
    (done, *_) = cycle.tick(ACTIVE)
    assert done.category == kinds.CAT_MEAL and done.excess_s == 0
    assert done.actual_s >= 25 * MIN


def test_refeicao_vale_tambem_no_lembrete_e_so_nas_fases_certas(cycle, clock):
    assert cycle.start_meal()  # aguardando
    cycle.end_break_early()
    reach_reminder(cycle, clock)
    assert cycle.phase is Phase.REMINDER and cycle.start_meal() and cycle.phase is Phase.BREAK
    assert not cycle.start_meal()  # já em descanso
    cycle.set_mode(Mode.CASUAL)
    assert not cycle.start_meal()
