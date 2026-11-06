"""Sensor real do Windows (nível B). É o único arquivo que chama a API do Windows.

Privacidade: lê CPU/RAM, o PID da janela em primeiro plano (para obter o nome do executável) e
há quanto tempo não há entrada de teclado/mouse. Não lê o título da janela nem as teclas, e não
guarda nada em disco.
"""

import ctypes
import datetime
from collections import deque
from collections.abc import Mapping
from ctypes import wintypes

import psutil

from pulso.clock import Clock, SystemClock
from pulso.sensors.base import UNKNOWN_CATEGORY, SensorFrame
from pulso.sensors.categories import categorize

_WINDOW_SECONDS = 60.0  # janela de contagem das trocas de programa


class _LastInputInfo(ctypes.Structure):
    """Estrutura de `GetLastInputInfo`: `dwTime` é o instante (em ms) da última entrada."""

    _fields_ = (("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD))


class WindowsSensor:
    def __init__(
        self, clock: Clock | None = None, extra_categories: Mapping[str, str] | None = None
    ) -> None:
        self._clock = clock or SystemClock()
        self._extra = extra_categories
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._kernel32.GetTickCount.restype = wintypes.DWORD
        self._user32.GetForegroundWindow.restype = wintypes.HWND
        self._last_process: str | None = None
        self._switch_times: deque[float] = deque()
        # A 1ª chamada de cpu_percent sempre devolve 0.0 (não há leitura anterior); "esquenta" aqui.
        psutil.cpu_percent(interval=None)

    def _foreground_process_name(self) -> str | None:
        """Nome do executável da janela em primeiro plano, ou None se não houver/acesso negado."""
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            return psutil.Process(pid.value).name()
        except (psutil.Error, OSError):
            return None

    def _idle_seconds(self) -> float:
        info = _LastInputInfo(cbSize=ctypes.sizeof(_LastInputInfo))
        if not self._user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        # Os dois contadores são de 32 bits e dão a volta (~49 dias); o módulo trata isso.
        elapsed_ms = (self._kernel32.GetTickCount() - info.dwTime) % (2**32)
        return elapsed_ms / 1000.0

    def _count_switches(self, process_name: str | None) -> int:
        """Conta trocas de programa no último minuto. Só guarda instantes, nunca nomes."""
        now = self._clock.now()
        if process_name is not None and process_name != self._last_process:
            if self._last_process is not None:
                self._switch_times.append(now)
            self._last_process = process_name
        while self._switch_times and now - self._switch_times[0] > _WINDOW_SECONDS:
            self._switch_times.popleft()
        return len(self._switch_times)

    def read(self) -> SensorFrame:
        process_name = self._foreground_process_name()
        category = categorize(process_name, self._extra) if process_name else UNKNOWN_CATEGORY
        now = datetime.datetime.now()
        return SensorFrame(
            cpu_percent=psutil.cpu_percent(interval=None),
            ram_percent=psutil.virtual_memory().percent,
            hour_of_day=now.hour + now.minute / 60.0,
            idle_seconds=self._idle_seconds(),
            category=category,
            app_switches_last_min=self._count_switches(process_name),
        )
