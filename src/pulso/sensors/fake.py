"""Sensor roteirizado: para testes e para rodar sem Windows."""

from collections.abc import Sequence

from pulso.sensors.base import SensorFrame


class ScriptedSensor:
    """Entrega as leituras do roteiro, em ordem; ao acabar, repete a última.

    Um item do roteiro que seja uma exceção é *lançada* na leitura (simula sensor com defeito).
    `calls` conta as chamadas a `read`, o que prova que a pausa de fato não lê nada.
    """

    def __init__(self, script: Sequence[SensorFrame | Exception]) -> None:
        if not script:
            raise ValueError("o roteiro precisa ter ao menos uma leitura")
        self._script = list(script)
        self.calls = 0

    def read(self) -> SensorFrame:
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item
