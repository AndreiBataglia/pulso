"""Sensor de reunião: o registro do Windows de mentira (chave de teste), nunca o real."""

import sys
import uuid

import pytest

from pulso.sensors.meeting import FakeMeetingSensor, WindowsMeetingSensor

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="registro do Windows")


@pytest.fixture
def consent_key():
    import winreg

    path = rf"Software\PulsoTeste-{uuid.uuid4().hex}\microphone"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path + r"\NonPackaged"):
        pass
    yield path
    for sub in (r"\NonPackaged\app.exe", r"\NonPackaged", r"\loja.app", ""):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path + sub)
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path.rsplit("\\", 1)[0])
    except OSError:
        pass


def _app(path, name, start, stop):
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, rf"{path}\{name}") as key:
        winreg.SetValueEx(key, "LastUsedTimeStart", 0, winreg.REG_QWORD, start)
        winreg.SetValueEx(key, "LastUsedTimeStop", 0, winreg.REG_QWORD, stop)


def test_sem_nenhum_programa_usando_o_microfone_nao_ha_reuniao(consent_key):
    _app(consent_key, r"NonPackaged\app.exe", start=133000, stop=133500)  # já parou
    assert WindowsMeetingSensor(consent_key).in_meeting() is False


def test_programa_comum_com_o_microfone_aberto_e_reuniao(consent_key):
    _app(consent_key, r"NonPackaged\app.exe", start=133000, stop=0)
    assert WindowsMeetingSensor(consent_key).in_meeting() is True


def test_app_da_loja_com_o_microfone_aberto_tambem_e_reuniao(consent_key):
    _app(consent_key, "loja.app", start=133000, stop=0)
    assert WindowsMeetingSensor(consent_key).in_meeting() is True


def test_chave_que_nao_existe_vale_sem_reuniao():
    assert WindowsMeetingSensor(r"Software\PulsoNaoExiste-xyz").in_meeting() is False


def test_sensor_falso_segue_o_roteiro_e_repete_o_ultimo_valor():
    sensor = FakeMeetingSensor([False, True])
    assert [sensor.in_meeting() for _ in range(4)] == [False, True, True, True]
