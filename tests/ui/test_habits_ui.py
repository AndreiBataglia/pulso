"""Hábitos na janela: lembretes, botões sempre à mão, nervoso e o ciclo do foco independente."""

import dataclasses
import random

import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.habits.focus_cycle import Mode, Phase
from pulso.sensors.fake import ScriptedSensor
from pulso.sensors.meeting import FakeMeetingSensor
from pulso.storage.brain_store import AutoSaver
from pulso.ui import phrases
from pulso.ui.main_window import MainWindow
from pulso.ui.tray import Tray
from tests.test_controller import FRAME, SpyEngine, make_habits

MIN = 60.0


class SpyTray(Tray):
    """Bandeja de verdade (menu incluso), mas que anota os avisos em vez de mostrá-los."""

    available = True  # fingimos que o Windows tem bandeja (offscreen não tem)

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def notify(self, text: str) -> None:
        self.messages.append(text)


def _build(tmp_path, meeting=None):
    clock = FakeClock()
    engine = SpyEngine()
    sensor = ScriptedSensor([FRAME])
    controller = PetController(
        sensor,
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, tmp_path / "c.npz", 1, clock),
        make_habits(clock),
        meeting,
    )
    return controller, sensor, clock


@pytest.fixture
def env(qapp, tmp_path):
    controller, _, clock = _build(tmp_path)
    tray = SpyTray()
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1), tray=tray)
    window.show()
    yield window, controller, clock, tray
    window.quit_app()


def _tick(window, clock, seconds):
    clock.advance(seconds)
    window.tick()


def _casual(window, controller):
    """Modo casual: sem ciclo do foco, só a água (o lembrete da pausa não atrapalha)."""
    controller.set_mode(Mode.CASUAL)
    window.tick()


def _reach_reminder(window, clock):
    _tick(window, clock, 1)  # a 1ª entrada abre o foco sozinha
    _tick(window, clock, 50 * MIN)


def _decline_twice(window, clock):
    """Recusa a água duas vezes: 4 pontos de pendência, acima do limite do nervoso."""
    for _ in range(2):
        _tick(window, clock, 60 * MIN)
        window.pet_tab.decline.click()


def test_bebi_e_carinho_sempre_visiveis_e_os_da_agua_escondidos(env):
    window, *_ = env
    tab = window.pet_tab
    assert tab.drink.isVisible() and tab.care.isVisible()
    assert not tab.later.isVisible() and not tab.decline.isVisible()


def test_lembrete_de_agua_fala_avisa_o_windows_e_mostra_depois_e_hoje_nao(env):
    window, controller, clock, notifier = env
    _casual(window, controller)
    _tick(window, clock, 60 * MIN)
    assert window.pet_tab.speech.text() == phrases.ASK_WATER
    assert notifier.messages == [phrases.ASK_WATER]
    assert window.pet_tab.later.isVisible() and window.pet_tab.decline.isVisible()


def test_bebi_responde_soma_o_copo_e_esconde_os_botoes_do_lembrete(env):
    window, controller, clock, _ = env
    _casual(window, controller)
    _tick(window, clock, 60 * MIN)
    window.pet_tab.drink.click()
    assert window.pet_tab.speech.text() == phrases.DRANK
    assert controller.habits.cups_today() == 1
    assert not window.pet_tab.later.isVisible()


def test_depois_adia_e_hoje_nao_recusa(env):
    window, controller, clock, _ = env
    _casual(window, controller)
    _tick(window, clock, 60 * MIN)
    window.pet_tab.later.click()
    assert window.pet_tab.speech.text() == phrases.LATER_AGAIN
    assert controller.habits.pending("water") == 0
    _tick(window, clock, 10 * MIN)
    window.pet_tab.decline.click()
    assert window.pet_tab.speech.text() == phrases.NO_PROBLEM
    assert controller.habits.pending("water") == 2


def test_pendencia_alta_deixa_o_pet_nervoso_e_a_legenda_diz_o_motivo(env):
    window, controller, clock, _ = env
    _casual(window, controller)
    _decline_twice(window, clock)
    assert controller.shown_mood == "nervoso"
    assert window.pet_tab.pet.target == "nervoso"
    assert "água" in window.pet_tab.caption.text()
    assert "água" in window.pet_tab.speech.text()


def test_o_nervoso_resiste_ao_humor_da_rede_ate_o_bebi(env):
    window, controller, clock, _ = env
    _casual(window, controller)
    _decline_twice(window, clock)
    for _ in range(30):  # a rede decide humores, mas o rosto não sai do nervoso
        _tick(window, clock, 1)
        assert window.pet_tab.pet.target == "nervoso"
    window.pet_tab.drink.click()
    assert window.pet_tab.pet.target != "nervoso"
    assert window.pet_tab.speech.text() == phrases.RELAXED
    assert not controller.habits.nervous


def test_o_foco_abre_sozinho_e_pular_leva_ao_lembrete(env):
    window, controller, clock, _ = env
    tab = window.pet_tab
    _tick(window, clock, 1)
    assert tab.state_label.text() == "FOCO" and tab.panel == "timer"
    _tick(window, clock, 10 * MIN)
    assert tab.timer_value.text() == "40:00"
    assert tab.take_break.isVisible() and tab.skip.isVisible()
    tab.skip.click()  # pula o foco: o pet pergunta do descanso
    assert controller.habits.asking == "break" and tab.panel == "reminder"
    assert tab.pause_now.isVisible() and tab.postpone.isVisible() and tab.decline_break.isVisible()
    assert not tab.drink.isVisible()  # o lembrete esconde a grade


def test_fim_do_foco_avisa_o_windows_e_pausar_agora_inicia_o_descanso(env):
    window, _, clock, notifier = env
    _reach_reminder(window, clock)
    assert phrases.ASK_BREAK in notifier.messages
    window.pet_tab.pause_now.click()
    assert window.pet_tab.panel == "rest" and window.pet_tab.state_label.text() == "DESCANSANDO"
    _tick(window, clock, 10 * MIN)
    assert notifier.messages[-1] == phrases.BACK_TO_WORK
    assert window.pet_tab.footer_left.text().startswith("1 pausa")


def test_prorrogar_e_recusar_a_pausa(env):
    window, controller, clock, _ = env
    _reach_reminder(window, clock)
    window.pet_tab.postpone.click()
    assert window.pet_tab.speech.text() == phrases.LATER_AGAIN
    assert "prorrogou 1×" in window.pet_tab.footer_left.text()
    _tick(window, clock, 10 * MIN)  # o lembrete volta
    window.pet_tab.decline_break.click()
    assert window.pet_tab.speech.text() == phrases.NO_PROBLEM
    assert controller.habits.pending("break") == 2


def test_ciclo_e_pausa_de_privacidade_sao_independentes(env):
    window, controller, clock, notifier = env
    _tick(window, clock, 1)
    window.toggle_pause()  # dono pausa a observação
    assert controller.paused
    _tick(window, clock, 50 * MIN)  # sem leitura, o foco congela: nada de lembrete
    assert controller.paused and controller.habits.cycle.phase is Phase.FOCUS
    assert phrases.ASK_BREAK not in notifier.messages
    window.toggle_pause()  # retomar a observação devolve o relógio ao foco
    assert controller.habits.cycle.phase is Phase.FOCUS


def test_passar_o_mouse_no_botao_faz_o_pet_dizer_o_que_ele_faz(env):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    window, *_ = env
    tab = window.pet_tab
    before = tab.speech.text()
    QApplication.sendEvent(tab.drink, QEvent(QEvent.Type.Enter))
    assert tab.speech.text() == tab.drink.toolTip() != before
    QApplication.sendEvent(tab.drink, QEvent(QEvent.Type.Leave))
    assert tab.speech.text() == before  # a fala de antes volta
    QApplication.sendEvent(tab.care, QEvent(QEvent.Type.Enter))
    tab.speech.setText("outra fala")  # alguém falou enquanto o mouse estava lá
    QApplication.sendEvent(tab.care, QEvent(QEvent.Type.Leave))
    assert tab.speech.text() == "outra fala"


def test_aceitar_a_pausa_poe_o_pet_para_descansar_e_bebi_o_faz_beber(env):
    window, _, clock, _ = env
    pet = window.pet_tab.pet
    _reach_reminder(window, clock)
    assert pet.activity is None  # perguntando: ainda não descansa
    window.pet_tab.pause_now.click()
    assert pet.shown == "descansando" and pet._countdown == "10:00"
    _tick(window, clock, 60)
    assert pet._countdown == "09:00"
    window.pet_tab.drink.click()
    assert pet.shown == "bebendo"
    _tick(window, clock, 10 * MIN)  # o descanso acabou: volta a focar
    pet.advance(20.0)
    assert pet.activity is None


def _away_and_back(window, sensor, clock):
    """10 min de foco, 22 min parado e a volta: o pet pergunta "o que foi?"."""
    _tick(window, clock, 1)
    _tick(window, clock, 10 * MIN)
    sensor._script = [dataclasses.replace(FRAME, idle_seconds=22 * MIN)]
    _tick(window, clock, 22 * MIN)
    sensor._script = [FRAME]
    _tick(window, clock, 1)


def test_voltar_de_uma_ausencia_pergunta_o_que_foi(qapp, tmp_path):
    controller, sensor, clock = _build(tmp_path)
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1))
    window.show()
    _away_and_back(window, sensor, clock)
    tab = window.pet_tab
    assert tab.panel == "away" and tab.state_label.text() == "VOLTOU · O QUE FOI?"
    assert not tab.drink.isVisible()
    tab.away_buttons["meal"].click()
    assert tab.panel == "timer" and controller.habits.breaks_today() == 1
    assert tab.speech.text() == phrases.AWAY_REPLIES["meal"]
    window.quit_app()


def test_botao_refeicao_fica_ao_lado_do_modo_e_comeca_o_descanso_longo(qapp, tmp_path):
    controller, sensor, clock = _build(tmp_path)
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1))
    window.show()
    _tick(window, clock, 2)
    tab = window.pet_tab
    assert tab.meal_button.isVisible() and tab.state_label.text() == "FOCO"
    tab.meal_button.click()
    assert tab.state_label.text() == "REFEIÇÃO" and tab.panel == "rest"
    assert not tab.meal_button.isVisible()
    assert tab.speech.text() == phrases.MEAL_STARTED
    tab.end_break.click()
    assert tab.panel == "timer" and controller.habits.breaks_today() == 1
    window.set_mode(Mode.CASUAL)
    assert not tab.meal_button.isVisible()
    window.quit_app()


def test_reuniao_pausa_o_foco_e_o_pet_avisa(qapp, tmp_path):
    meeting = FakeMeetingSensor([False])
    controller, _, clock = _build(tmp_path, meeting)
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1))
    window.show()
    _tick(window, clock, 1)
    meeting._script = [True]
    _tick(window, clock, 1)
    tab = window.pet_tab
    assert tab.state_label.text() == "EM REUNIÃO" and tab.speech.text() == phrases.MEETING_ON
    meeting._script = [False]
    _tick(window, clock, 1)
    assert tab.state_label.text() == "FOCO" and tab.speech.text() == phrases.MEETING_OFF
    window.quit_app()


def test_modo_casual_troca_o_cartao_pela_agua_e_volta(env):
    window, controller, clock, _ = env
    _tick(window, clock, 1)
    window.toggle_mode()
    tab = window.pet_tab
    assert tab.state_label.text() == "MODO CASUAL" and tab.speech.text() == phrases.CASUAL_ON
    assert "min" in tab.timer_value.text() and not tab.skip.isVisible()
    window.toggle_mode()
    assert tab.speech.text() == phrases.PROFESSIONAL_ON
    assert controller.habits.mode is Mode.PROFESSIONAL


def test_prorrogar_de_novo_deixa_preocupado_e_o_balao_diz_o_motivo(env):
    window, controller, clock, _ = env
    _reach_reminder(window, clock)
    window.pet_tab.postpone.click()
    assert window.pet_tab.pet.target == "preocupado"
    assert "1 vez" in window.pet_tab.caption.text()
    _tick(window, clock, 5 * MIN)  # o lembrete volta
    window.pet_tab.postpone.click()
    assert "2 vezes" in window.pet_tab.speech.text()
    assert "2 vezes" in window.pet_tab.caption.text()


def test_muito_tempo_sem_mexer_deixa_sonolento_com_o_motivo(env):
    window, controller, clock, _ = env
    controller._loop._sensor._script = [dataclasses.replace(FRAME, idle_seconds=8 * MIN)]
    _casual(window, controller)
    window.tick()
    assert window.pet_tab.pet.target == "sonolento"
    assert "8 min" in window.pet_tab.caption.text()


def test_agua_sem_resposta_avisa_que_ficou_pendente_e_insiste_em_10_min(env):
    window, controller, clock, _ = env
    _casual(window, controller)
    _tick(window, clock, 60 * MIN)
    assert window.pet_tab.speech.text() == phrases.ASK_WATER
    _tick(window, clock, 5 * MIN)  # ninguém respondeu
    assert window.pet_tab.speech.text() == phrases.WATER_IGNORED
    assert controller.habits.pending("water") == 1
    _tick(window, clock, 10 * MIN)
    assert window.pet_tab.speech.text() == phrases.ASK_WATER


def test_rodape_mostra_a_agua_em_ml_e_litros(env):
    window, controller, clock, _ = env
    window.tick()
    assert "0 ml" in window.pet_tab.footer_right.text()
    for _ in range(3):
        window.pet_tab.drink.click()
        clock.advance(10)
    assert "750 ml" in window.pet_tab.footer_right.text()
    window.pet_tab.drink.click()
    assert "1 L" in window.pet_tab.footer_right.text()


def test_foco_vencido_com_a_rede_esperando_explica_na_tela(env):
    window, controller, clock, _ = env
    controller._decoder.mood = "esperar"
    _tick(window, clock, 1)
    _tick(window, clock, 50 * MIN)
    assert window.pet_tab.timer_value.text() == "00:00"
    assert "esperando a hora de avisar" in window.pet_tab.timer_caption.text()
