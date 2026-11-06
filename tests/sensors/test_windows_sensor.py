"""Teste de fumaça do sensor real: só no Windows e só confere formas e faixas, nunca valores."""

import sys

import pytest

from pulso.clock import FakeClock

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="sensor só existe no Windows")


def test_read_returns_sane_frame():
    from pulso.sensors.windows import WindowsSensor

    frame = WindowsSensor(FakeClock()).read()
    assert frame.valid
    assert 0.0 <= frame.cpu_percent <= 100.0
    assert 0.0 <= frame.ram_percent <= 100.0
    assert 0.0 <= frame.hour_of_day < 24.0
    assert frame.idle_seconds >= 0.0
    assert isinstance(frame.category, str)
    assert frame.app_switches_last_min == 0  # 1ª leitura: ainda não houve troca


def test_switch_counter_counts_and_expires():
    from pulso.sensors.windows import WindowsSensor

    clock = FakeClock()
    sensor = WindowsSensor(clock)
    assert sensor._count_switches("a.exe") == 0  # primeiro programa visto não é troca
    assert sensor._count_switches("a.exe") == 0
    assert sensor._count_switches("b.exe") == 1
    assert sensor._count_switches("a.exe") == 2
    clock.advance(61)
    assert sensor._count_switches("a.exe") == 0  # as trocas antigas saíram da janela de 60 s
