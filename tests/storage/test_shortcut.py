"""Atalho do Menu Iniciar: os testes criam o `.lnk` numa pasta temporária, nunca no Menu real."""

import os
import sys

import pytest

from pulso.storage.shortcut import SHORTCUT_NAME, create_shortcut, start_menu_shortcut


def test_o_atalho_fica_na_pasta_programas_do_menu_iniciar(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    lnk = start_menu_shortcut()
    assert lnk.name == SHORTCUT_NAME
    assert lnk.parent == tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs"


@pytest.mark.skipif(sys.platform != "win32", reason="atalho .lnk do Windows")
def test_cria_o_lnk_com_alvo_e_argumentos_certos(tmp_path):
    lnk = create_shortcut(tmp_path / "pasta" / "Pulso.lnk", target=tmp_path / "x.exe")
    assert lnk.exists()
    out = (
        os.popen(  # lê de volta o que o Windows gravou
            f'powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell)'
            f".CreateShortcut('{lnk}'); $s.TargetPath; $s.Arguments\""
        )
        .read()
        .split("\n")
    )
    assert out[0].strip() == str(tmp_path / "x.exe")
    assert out[1].strip() == "-m pulso"
