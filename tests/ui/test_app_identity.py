"""Identidade do app no Windows e o argumento `--minimizado` (abrir só na bandeja)."""

import ctypes
import sys

import pytest

from pulso.__main__ import main
from pulso.ui import app as app_module


@pytest.mark.skipif(sys.platform != "win32", reason="AppUserModelID é coisa do Windows")
def test_o_processo_ganha_o_id_proprio_do_pulso():
    assert app_module.set_app_id()
    buffer = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(buffer))
    assert result == 0 and buffer.value == app_module.APP_ID == "AndreiBataglia.Pulso"
    ctypes.windll.ole32.CoTaskMemFree(buffer)


@pytest.mark.parametrize(("argv", "minimized"), [([], False), (["--minimizado"], True)])
def test_minimizado_chega_ate_o_run(monkeypatch, argv, minimized):
    chamadas = []
    monkeypatch.setattr(app_module, "run", lambda **kwargs: chamadas.append(kwargs) or 0)
    assert main(argv) == 0
    assert chamadas == [{"fake_sensors": False, "minimized": minimized}]
