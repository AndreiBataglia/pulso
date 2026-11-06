"""Bandeja e opções da janela: X esconde, Sair encerra, sempre à frente, água e Windows."""

import random

import pytest
from PySide6.QtCore import Qt

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
from pulso.storage.brain_store import AutoSaver
from pulso.storage.config import Settings
from pulso.ui import phrases
from pulso.ui.main_window import MainWindow
from tests.test_controller import FRAME, SpyEngine, make_habits
from tests.ui.test_habits_ui import SpyTray

MIN = 60.0


class FakeAutostart:
    """Registro do Windows de mentira: nunca toca no do dono."""

    def __init__(self, fail: bool = False) -> None:
        self._on = False
        self.fail = fail

    def enabled(self) -> bool:
        return self._on

    def set_enabled(self, on: bool) -> None:
        if self.fail:
            raise OSError("recusado")
        self._on = on


@pytest.fixture
def env(qapp, tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    path = tmp_path / "c.npz"
    controller = PetController(
        ScriptedSensor([FRAME]),
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, path, 1, clock),
        make_habits(clock),
    )
    saved: list[Settings] = []
    tray, autostart = SpyTray(), FakeAutostart()
    window = MainWindow(
        controller,
        clock,
        tick_ms=3_600_000,
        rng=random.Random(1),
        tray=tray,
        settings=Settings(),
        save_settings=saved.append,
        autostart=autostart,
    )
    window.show()
    yield window, controller, clock, tray, autostart, saved, path
    window.quit_app()


def _action(tray, text):
    return next(a for a in tray.menu.actions() if a.text() == text)


def test_o_x_esconde_na_bandeja_e_continua_rodando(env):
    window, controller, clock, tray, *_ = env
    window.close()
    assert window.isHidden()
    assert tray.messages == [phrases.IN_TRAY]  # avisa na primeira vez
    window.tick()  # o laço e os lembretes seguem
    clock.advance(60 * MIN)
    window.tick()
    assert controller.habits.water.asking
    assert window._timer.isActive()  # o laço de 1 s não parou


def test_o_aviso_de_bandeja_so_aparece_uma_vez(env):
    window, _, _, tray, *_ = env
    window.close()
    window.show()
    window.close()
    assert tray.messages == [phrases.IN_TRAY]


def test_notificacao_com_a_janela_escondida_chega_na_bandeja(env):
    window, _, clock, tray, *_ = env
    window.close()
    clock.advance(60 * MIN)
    window.tick()
    assert phrases.ASK_WATER in tray.messages


def test_sair_de_verdade_guarda_o_cerebro_e_fecha(env):
    window, _, _, _, _, _, path = env
    window.quit_app()
    assert path.exists()  # shutdown() gravou
    assert not window.isVisible()


def test_sem_bandeja_o_x_encerra_como_antes(qapp, tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    path = tmp_path / "c.npz"
    controller = PetController(
        ScriptedSensor([FRAME]), clock, engine, MoodDecoder(engine.groups), RewardRules(clock),
        AutoSaver(engine, path, 1, clock), make_habits(clock),
    )  # fmt: skip
    window = MainWindow(controller, clock, tick_ms=3_600_000)
    window.show()
    window.close()
    assert path.exists()


def test_o_fim_da_sessao_do_windows_nao_fica_preso_no_x(env):
    window, _, _, _, _, _, path = env
    window.prepare_to_quit()
    window.close()
    assert path.exists()


def test_sempre_a_frente_comeca_ligado_e_o_menu_liga_e_desliga(env):
    window, _, _, tray, _, saved, _ = env
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    action = _action(tray, "Sempre à frente")
    assert action.isChecked()
    action.trigger()  # desmarca
    assert not window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert saved[-1].always_on_top is False
    assert window.isVisible()  # trocar a flag não deixa a janela escondida
    action.trigger()
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert saved[-1].always_on_top is True


def test_preferencia_salva_de_nao_ficar_a_frente_e_respeitada(qapp, tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    controller = PetController(
        ScriptedSensor([FRAME]), clock, engine, MoodDecoder(engine.groups), RewardRules(clock),
        AutoSaver(engine, tmp_path / "c.npz", 1, clock), make_habits(clock),
    )  # fmt: skip
    window = MainWindow(
        controller, clock, tick_ms=3_600_000, tray=SpyTray(), settings=Settings(always_on_top=False)
    )
    assert not window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    window.quit_app()


def test_desligar_a_agua_para_o_lembrete_e_guarda_a_escolha(env):
    window, controller, clock, tray, _, saved, _ = env
    _action(tray, "Lembrete de água").trigger()  # desmarca
    assert saved[-1].water_enabled is False
    clock.advance(120 * MIN)
    window.tick()
    assert not controller.habits.water.asking
    _action(tray, "Lembrete de água").trigger()  # liga de novo: recomeça um intervalo inteiro
    clock.advance(59 * MIN)
    window.tick()
    assert not controller.habits.water.asking
    clock.advance(1 * MIN)
    window.tick()
    assert controller.habits.water.asking


def test_desligar_a_agua_some_com_o_balao_que_estava_na_tela(env):
    window, controller, clock, tray, *_ = env
    clock.advance(60 * MIN)
    window.tick()
    assert window.pet_tab.later.isVisible()
    _action(tray, "Lembrete de água").trigger()
    assert not controller.habits.water.asking
    assert not window.pet_tab.later.isVisible()


def test_iniciar_com_o_windows_liga_desliga_e_reflete_o_registro(env):
    _, _, _, tray, autostart, *_ = env
    action = _action(tray, "Iniciar com o Windows")
    assert not action.isChecked()
    action.trigger()
    assert autostart.enabled()
    action.trigger()
    assert not autostart.enabled()


def test_se_o_windows_recusar_o_aviso_aparece_e_o_visto_volta(env):
    window, _, _, tray, autostart, *_ = env
    autostart.fail = True
    action = _action(tray, "Iniciar com o Windows")
    action.trigger()  # tentou marcar
    assert not action.isChecked()
    assert "Não consegui" in window.pet_tab.speech.text()


def test_o_menu_atualiza_os_textos_de_pausa_e_pomodoro(env):
    window, _, _, tray, *_ = env
    pomodoro_menu = next(a for a in tray.menu.actions() if a.text() == "Pomodoro").menu()
    toggle, skip = pomodoro_menu.actions()
    window._refresh_tray_menu()
    assert toggle.text() == "Iniciar" and not skip.isEnabled()
    toggle.trigger()
    window._refresh_tray_menu()
    assert toggle.text() == "Pausar" and skip.isEnabled()
    toggle.trigger()
    window._refresh_tray_menu()
    assert toggle.text() == "Continuar"
    pause = _action(tray, "Pausar observação")
    pause.trigger()
    window._refresh_tray_menu()
    assert pause.text() == "Retomar observação"
    assert window._controller.paused
