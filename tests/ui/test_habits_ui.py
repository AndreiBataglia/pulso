"""Hábitos na janela: lembretes, botões sempre à mão, nervoso e o pomodoro independente."""

import random

import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
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


@pytest.fixture
def env(qapp, tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    controller = PetController(
        ScriptedSensor([FRAME]),
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, tmp_path / "c.npz", 1, clock),
        make_habits(clock),
    )
    tray = SpyTray()
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1), tray=tray)
    window.show()
    yield window, controller, clock, tray
    window.quit_app()


def _tick(window, clock, seconds):
    clock.advance(seconds)
    window.tick()


def _decline_twice(window, clock):
    """Recusa a água duas vezes: 4 pontos de pendência, acima do limite do nervoso."""
    for _ in range(2):
        _tick(window, clock, 60 * MIN)
        window.pet_tab.decline.click()


def test_botoes_bebi_e_fiz_a_pausa_sempre_visiveis_e_os_outros_escondidos(env):
    window, *_ = env
    tab = window.pet_tab
    assert tab.drink.isVisible() and tab.rested.isVisible()
    assert not tab.later.isVisible() and not tab.decline.isVisible()


def test_lembrete_de_agua_fala_avisa_o_windows_e_mostra_depois_e_hoje_nao(env):
    window, _, clock, notifier = env
    _tick(window, clock, 60 * MIN)
    assert window.pet_tab.speech.text() == phrases.ASK_WATER
    assert notifier.messages == [phrases.ASK_WATER]
    assert window.pet_tab.later.isVisible() and window.pet_tab.decline.isVisible()


def test_bebi_responde_soma_o_copo_e_esconde_os_botoes_do_lembrete(env):
    window, controller, clock, _ = env
    _tick(window, clock, 60 * MIN)
    window.pet_tab.drink.click()
    assert window.pet_tab.speech.text() == phrases.DRANK
    assert controller.habits.cups_today() == 1
    assert not window.pet_tab.later.isVisible()


def test_depois_adia_e_hoje_nao_recusa(env):
    window, controller, clock, _ = env
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
    _decline_twice(window, clock)
    assert controller.shown_mood == "nervoso"
    assert window.pet_tab.pet.target == "nervoso"
    assert "água" in window.pet_tab.caption.text()
    assert "água" in window.pet_tab.speech.text()


def test_o_nervoso_resiste_ao_humor_da_rede_ate_o_bebi(env):
    window, controller, clock, _ = env
    _decline_twice(window, clock)
    for _ in range(30):  # a rede decide humores, mas o rosto não sai do nervoso
        _tick(window, clock, 1)
        assert window.pet_tab.pet.target == "nervoso"
    window.pet_tab.drink.click()
    assert window.pet_tab.pet.target != "nervoso"
    assert window.pet_tab.speech.text() == phrases.RELAXED
    assert not controller.habits.nervous


def test_pomodoro_iniciar_pausar_continuar_e_pular(env):
    window, controller, clock, _ = env
    tab = window.pet_tab
    assert not tab.pomodoro_skip.isEnabled()
    tab.pomodoro_toggle.click()
    assert "Foco 50:00" in tab.pomodoro_label.text() and tab.pomodoro_toggle.toolTip() == "Pausar"
    _tick(window, clock, 10 * MIN)
    assert "Foco 40:00" in tab.pomodoro_label.text()
    tab.pomodoro_toggle.click()
    assert "(pausado)" in tab.pomodoro_label.text() and tab.pomodoro_toggle.toolTip() == "Continuar"
    _tick(window, clock, 20 * MIN)
    assert "Foco 40:00" in tab.pomodoro_label.text()  # congelado
    tab.pomodoro_toggle.click()
    tab.pomodoro_skip.click()  # pula o foco: o pet pergunta do descanso
    assert controller.habits.asking == "break"
    assert tab.later.isVisible()


def test_fim_do_foco_avisa_o_windows_e_fiz_a_pausa_inicia_o_descanso(env):
    window, _, clock, notifier = env
    window.pet_tab.pomodoro_toggle.click()
    _tick(window, clock, 50 * MIN)
    assert phrases.ASK_BREAK in notifier.messages
    window.pet_tab.rested.click()
    assert "Descanso 10:00" in window.pet_tab.pomodoro_label.text()
    _tick(window, clock, 10 * MIN)
    assert notifier.messages[-1] == phrases.BACK_TO_WORK


def test_pomodoro_e_pausa_de_privacidade_sao_independentes(env):
    window, controller, clock, notifier = env
    window.pet_tab.pomodoro_toggle.click()
    window.toggle_pause()  # dono pausa a observação
    assert controller.paused
    _tick(window, clock, 50 * MIN)  # o pomodoro segue e avisa, mesmo com o pet dormindo
    assert controller.paused
    assert phrases.ASK_BREAK in notifier.messages
    window.pet_tab.rested.click()  # responder também não religa a observação
    assert controller.paused
    window.toggle_pause()  # e retomar a observação não mexe no pomodoro
    assert "Descanso" in window.pet_tab.pomodoro_label.text()


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
    window.pet_tab.pomodoro_toggle.click()
    _tick(window, clock, 50 * MIN)
    assert pet.activity is None  # perguntando: ainda não descansa
    window.pet_tab.rested.click()
    assert pet.shown == "descansando" and pet._countdown == "10:00"
    _tick(window, clock, 60)
    assert pet._countdown == "09:00"
    window.pet_tab.drink.click()
    assert pet.shown == "bebendo"
    _tick(window, clock, 10 * MIN)  # o descanso acabou: volta a focar
    pet.advance(20.0)
    assert pet.activity is None
