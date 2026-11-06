"""`config.toml` (preferências) e "iniciar com o Windows" (chave de teste, nunca a `Run` real)."""

import sys
import uuid

import pytest

from pulso.storage.autostart import VALUE_NAME, Autostart, default_command
from pulso.storage.config import Settings, load_settings, save_settings


def test_sem_arquivo_vale_o_padrao(tmp_path):
    assert load_settings(tmp_path / "nada.toml") == Settings()
    assert Settings().always_on_top and Settings().water_enabled


def test_gravar_e_ler_de_volta(tmp_path):
    path = tmp_path / "pasta" / "config.toml"  # a pasta é criada
    save_settings(path, Settings(always_on_top=False, water_enabled=False))
    assert load_settings(path) == Settings(always_on_top=False, water_enabled=False)
    assert not list(path.parent.glob("*.tmp"))  # sem lixo da gravação atômica


def test_arquivo_quebrado_nao_impede_de_abrir(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("isto = = não é toml", encoding="utf-8")
    assert load_settings(path) == Settings()


def test_tipo_errado_volta_ao_padrao_so_naquele_campo(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[window]\nalways_on_top = "sim"\n[habits]\nwater_enabled = false\n', encoding="utf-8"
    )
    assert load_settings(path) == Settings(always_on_top=True, water_enabled=False)


def test_comando_de_inicio_usa_o_mesmo_python_e_o_modulo():
    command = default_command()
    assert command.endswith(" -m pulso") and command.startswith('"')
    assert sys.executable.lower().replace("python.exe", "") in command.lower().replace(
        "pythonw.exe", ""
    )


@pytest.mark.skipif(sys.platform != "win32", reason="registro do Windows")
def test_ligar_e_desligar_na_chave_de_teste():
    import winreg

    key_path = rf"Software\PulsoTeste-{uuid.uuid4().hex}"
    autostart = Autostart(key_path, command='"x.exe" -m pulso')
    try:
        assert not autostart.enabled()
        autostart.set_enabled(True)
        assert autostart.enabled()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            assert winreg.QueryValueEx(key, VALUE_NAME)[0] == '"x.exe" -m pulso'
        autostart.set_enabled(False)
        assert not autostart.enabled()
        autostart.set_enabled(False)  # desligar o que já está desligado não dá erro
    finally:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except OSError:
            pass
