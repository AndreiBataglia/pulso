"""Remover o Pulso pela janela e pelo comando. Tudo em pastas temporárias, com registro falso."""

import random

import pytest
from PySide6.QtWidgets import QMessageBox

from pulso.__main__ import main
from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
from pulso.storage import uninstall
from pulso.storage.brain_store import AutoSaver
from pulso.storage.config import Settings
from pulso.ui.main_window import MainWindow
from pulso.ui.remove_dialog import RemoveDialog
from pulso.ui.settings_dialog import REMOVE_CODE, SettingsDialog
from tests.storage.test_uninstall import FakeAutostart
from tests.test_controller import FRAME, SpyEngine, make_habits
from tests.ui.test_habits_ui import SpyTray


def test_botao_remover_nos_ajustes_devolve_o_codigo_de_remocao(qapp):
    dialog = SettingsDialog(Settings())
    dialog.remove_button.click()
    assert dialog.result() == REMOVE_CODE
    dialog.close()


def test_confirmacao_so_libera_digitando_remover(qapp, tmp_path):
    dialog = RemoveDialog(tmp_path, ["Pasta de dados: x"])
    assert not dialog.ok_button.isEnabled()
    dialog.confirm.setText("remo")
    assert not dialog.ok_button.isEnabled()
    dialog.confirm.setText("REMOVER")
    assert dialog.ok_button.isEnabled()
    dialog.close()


def test_confirmacao_oferece_backup(qapp, tmp_path):
    data = tmp_path / "Pulso"
    data.mkdir()
    (data / "cerebro.npz").write_bytes(b"x")
    dialog = RemoveDialog(data, [])
    dialog.make_backup(tmp_path / "bkp")
    assert dialog.backup_path is not None and dialog.backup_path.exists()
    assert "Backup guardado" in dialog.backup_label.text()
    dialog.close()


@pytest.fixture
def env(qapp, tmp_path, monkeypatch):
    data = tmp_path / "Pulso"
    data.mkdir()
    brain = data / "cerebro.npz"
    clock = FakeClock()
    engine = SpyEngine()
    controller = PetController(
        ScriptedSensor([FRAME]),
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, brain, 1, clock),
        make_habits(clock),
    )
    (data / "config.toml").write_text("[habits]\n", encoding="utf-8")
    shortcut = tmp_path / "Pulso.lnk"
    shortcut.write_bytes(b"lnk")
    autostart = FakeAutostart(on=True)
    monkeypatch.setattr("pulso.ui.main_window.data_dir", lambda: data)
    monkeypatch.setattr("pulso.ui.main_window.start_menu_shortcut", lambda: shortcut)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    window = MainWindow(
        controller,
        clock,
        tick_ms=3_600_000,
        rng=random.Random(1),
        tray=SpyTray(),
        settings=Settings(),
        autostart=autostart,
    )
    window.show()
    yield window, controller, data, shortcut, autostart
    window.quit_app()


def test_remover_apaga_tudo_e_o_cerebro_nao_volta_ao_sair(env, monkeypatch):
    window, controller, data, shortcut, autostart = env
    controller.shutdown()  # (grava o cérebro uma vez, como no uso normal)
    assert (data / "cerebro.npz").exists()
    monkeypatch.setattr(window, "_confirm_removal", lambda folder, lines: True)
    window.remove_pulso()
    assert not data.exists() and not shortcut.exists() and not autostart.on
    window.quit_app()  # sair de novo: o closeEvent não pode regravar o cérebro
    assert not data.exists()


def test_cancelar_a_confirmacao_nao_apaga_nada(env, monkeypatch):
    window, _, data, shortcut, autostart = env
    monkeypatch.setattr(window, "_confirm_removal", lambda folder, lines: False)
    window.remove_pulso()
    assert (data / "config.toml").exists() and shortcut.exists() and autostart.on


def test_pasta_suspeita_nao_chega_nem_a_pedir_confirmacao(env, monkeypatch, tmp_path):
    window, _, _, _, _ = env
    outra = tmp_path / "Documentos"
    outra.mkdir()
    monkeypatch.setattr("pulso.ui.main_window.data_dir", lambda: outra)
    monkeypatch.setattr(
        window, "_confirm_removal", lambda *a: pytest.fail("não devia pedir confirmação")
    )
    window.remove_pulso()
    assert outra.exists()


# ---- linha de comando ----------------------------------------------------------------------


def test_comando_remover_pede_confirmacao_e_cancela_se_digitar_outra_coisa(
    tmp_path, monkeypatch, capsys
):
    data = tmp_path / "Pulso"
    data.mkdir()
    (data / "cerebro.npz").write_bytes(b"x")
    monkeypatch.setenv("PULSO_DATA_DIR", str(data))
    monkeypatch.setattr("builtins.input", lambda prompt="": "nao")
    assert main(["--remover"]) == 1
    assert (data / "cerebro.npz").exists()
    assert "Nada foi apagado" in capsys.readouterr().out


def test_comando_remover_com_backup_apaga_depois_de_confirmar(tmp_path, monkeypatch, capsys):
    data = tmp_path / "Pulso"
    data.mkdir()
    (data / "cerebro.npz").write_bytes(b"x")
    monkeypatch.setenv("PULSO_DATA_DIR", str(data))
    monkeypatch.setattr("builtins.input", lambda prompt="": uninstall.CONFIRMATION)
    monkeypatch.setattr("pulso.storage.autostart.Autostart.enabled", lambda self: False)
    monkeypatch.setattr(
        "pulso.storage.shortcut.start_menu_shortcut", lambda: tmp_path / "Pulso.lnk"
    )
    assert main(["--remover", "--backup-para", str(tmp_path / "bkp")]) == 0
    assert not data.exists()
    assert list((tmp_path / "bkp").glob("pulso-backup-*.zip"))
    assert "Backup guardado" in capsys.readouterr().out
