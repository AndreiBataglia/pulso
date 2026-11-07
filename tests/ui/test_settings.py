"""Ajustes: tempos e regras automáticas, aplicados sem reiniciar e guardados no config."""

import random

import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
from pulso.storage.brain_store import AutoSaver
from pulso.storage.config import RANGES, Settings, habit_config, load_settings, save_settings
from pulso.ui.main_window import MainWindow
from pulso.ui.settings_dialog import SettingsDialog
from tests.test_controller import FRAME, SpyEngine, make_habits
from tests.ui.test_habits_ui import SpyTray

MIN = 60.0


def test_config_guarda_e_le_os_tempos(tmp_path):
    path = tmp_path / "config.toml"
    mine = Settings(focus_min=25, break_min=5, long_break_min=15, water_interval_min=45)
    save_settings(path, mine)
    assert load_settings(path) == mine
    assert "focus_min = 25" in path.read_text(encoding="utf-8")


def test_tempo_fora_do_intervalo_ou_de_tipo_errado_volta_ao_padrao(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[habits]\nfocus_min = 9999\nbreak_min = "dez"\nlong_break_min = true\n'
        "water_interval_min = 30\n",
        encoding="utf-8",
    )
    loaded = load_settings(path)
    assert loaded.focus_min == 50 and loaded.break_min == 10 and loaded.long_break_min == 20
    assert loaded.water_interval_min == 30


def test_padroes_batem_com_o_plano_e_estao_dentro_dos_intervalos():
    s = Settings()
    assert (s.focus_min, s.break_min, s.long_break_min, s.water_interval_min) == (50, 10, 20, 60)
    for name, (low, high) in RANGES.items():
        assert low <= getattr(s, name) <= high


def test_habit_config_leva_os_tempos():
    cfg = habit_config(Settings(focus_min=25, water_interval_min=30))
    assert cfg.focus_min == 25 and cfg.water_interval_min == 30 and cfg.cycles_before_long == 4


def test_dialogo_devolve_o_que_esta_na_tela(qapp):
    dialog = SettingsDialog(Settings())
    dialog.spins["focus_min"].setValue(25)
    dialog.spins["water_interval_min"].setValue(30)
    result = dialog.settings()
    assert result.focus_min == 25 and result.water_interval_min == 30
    assert result.always_on_top  # o que a tela não mexe fica como estava
    dialog.close()


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
    saved: list[Settings] = []
    window = MainWindow(
        controller,
        clock,
        tick_ms=3_600_000,
        rng=random.Random(1),
        tray=SpyTray(),
        settings=Settings(),
        save_settings=saved.append,
    )
    window.show()
    yield window, controller, clock, saved
    window.quit_app()


def test_foco_novo_vale_ja(env):
    window, _, _, saved = env
    window.apply_settings(Settings(focus_min=25))
    assert saved[-1].focus_min == 25
    window.tick()  # a 1ª entrada abre o foco sozinha, já com o tempo novo
    assert window.pet_tab.timer_value.text() == "25:00"


def test_intervalo_novo_da_agua_vale_na_hora(env):
    window, controller, clock, _ = env
    window.apply_settings(Settings(water_interval_min=30))
    clock.advance(29 * MIN)
    window.tick()
    assert not controller.habits.water.asking
    clock.advance(1 * MIN)
    window.tick()
    assert controller.habits.water.asking


def test_bandeja_tem_ajustes_e_a_janela_tem_a_engrenagem(env):
    window, *_ = env
    assert window.settings_button.toolTip().startswith("Ajustes")
    assert any(a.text() == "Ajustes…" for a in window._tray.menu.actions())


def test_o_app_comeca_com_os_tempos_do_config(tmp_path):
    from pulso.ui.app import build_controller

    controller, _ = build_controller(
        ScriptedSensor([FRAME]),
        FakeClock(),
        tmp_path / "cerebro.npz",
        settings=Settings(focus_min=25),
    )
    assert controller.habits.cfg.focus_min == 25
    padrao, _ = build_controller(ScriptedSensor([FRAME]), FakeClock(), tmp_path / "outro.npz")
    assert padrao.habits.cfg.focus_min == 50


def test_modo_e_ausencia_vao_para_o_config_e_sao_validados(tmp_path):
    path = tmp_path / "config.toml"
    mine = Settings(mode="casual", away_min=8)
    save_settings(path, mine)
    assert load_settings(path) == mine
    assert 'mode = "casual"' in path.read_text(encoding="utf-8")
    assert habit_config(mine).away_idle_s == 8 * 60
    path.write_text('[habits]\nmode = "turbo"\naway_min = 999\n', encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.mode == "profissional" and loaded.away_min == 5  # inválidos voltam ao padrão


def test_dialogo_devolve_modo_e_ausencia(qapp):
    dialog = SettingsDialog(Settings())
    dialog.mode.setCurrentIndex(dialog.mode.findData("casual"))
    dialog.spins["away_min"].setValue(12)
    result = dialog.settings()
    assert result.mode == "casual" and result.away_min == 12
    dialog.close()


def test_tamanho_do_recipiente_e_guardado_validado_e_chega_aos_habitos(tmp_path):
    path = tmp_path / "config.toml"
    save_settings(path, Settings(water_ml=500))
    assert load_settings(path).water_ml == 500
    assert habit_config(Settings(water_ml=500)).water_ml == 500
    path.write_text("[habits]\nwater_ml = 99999\n", encoding="utf-8")
    assert load_settings(path).water_ml == 250  # fora do intervalo: volta ao padrão
