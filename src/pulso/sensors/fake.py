"""Sensor roteirizado: para testes e para rodar sem Windows."""

from collections.abc import Sequence

from pulso.sensors.base import SensorFrame


def demo_scenario(seconds_each: int = 60) -> list[SensorFrame]:
    """Quatro "momentos do dia" bem diferentes, para ver o humor mudar sem ler o PC de verdade."""
    moments = [
        # trabalhando: código, CPU média, mexendo sem parar, de manhã
        SensorFrame(45.0, 60.0, 10.0, 0.0, "codigo", 3),
        # distraído: vídeo à tarde, quase sem mexer
        SensorFrame(20.0, 55.0, 15.0, 120.0, "video", 0),
        # conversando: chat, muitas trocas de programa
        SensorFrame(30.0, 58.0, 17.0, 5.0, "chat", 9),
        # de madrugada: ocioso há muito tempo, máquina parada
        SensorFrame(3.0, 40.0, 2.0, 900.0, "outro", 0),
    ]
    return [frame for frame in moments for _ in range(seconds_each)]


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
