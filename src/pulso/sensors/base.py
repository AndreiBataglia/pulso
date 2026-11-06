"""O que um sensor entrega (`SensorFrame`) e o contrato que todo sensor cumpre (`Sensor`)."""

from dataclasses import dataclass
from typing import Protocol

# Categoria usada quando não se sabe o que está em primeiro plano.
UNKNOWN_CATEGORY = "outro"


@dataclass(frozen=True)
class SensorFrame:
    """Uma leitura de 1 s. Só metadados: nunca título de janela nem teclas."""

    cpu_percent: float  # 0–100
    ram_percent: float  # 0–100
    hour_of_day: float  # 0–24 (ex.: 14.5 = 14h30)
    idle_seconds: float  # segundos desde a última entrada de teclado/mouse
    category: str  # categoria do programa em primeiro plano
    app_switches_last_min: int  # trocas de programa no último minuto
    valid: bool = True  # False = a leitura falhou; os demais campos são neutros

    @classmethod
    def unknown(cls) -> "SensorFrame":
        """Leitura "desconhecida": valores neutros, usada quando o sensor falha."""
        return cls(0.0, 0.0, 0.0, 0.0, UNKNOWN_CATEGORY, 0, valid=False)


class Sensor(Protocol):
    """Contrato de um sensor: devolve uma leitura a cada chamada."""

    def read(self) -> SensorFrame: ...
