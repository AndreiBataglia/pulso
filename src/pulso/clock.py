"""Relógio injetável: o código nunca chama `time` direto, para os testes controlarem o tempo."""

import time
from typing import Protocol


class Clock(Protocol):
    """Contrato de um relógio: dizer que horas são e esperar."""

    def now(self) -> float:
        """Segundos desde um ponto qualquer (só diferenças importam)."""
        ...

    def sleep(self, seconds: float) -> None:
        """Espera `seconds` segundos."""
        ...


class SystemClock:
    """Relógio real: `monotonic` nunca anda para trás, ao contrário do relógio de parede."""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock:
    """Relógio falso: o tempo só passa quando o teste manda; `sleep` avança sem esperar."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self._now += seconds
