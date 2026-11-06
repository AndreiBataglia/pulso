"""Laço mínimo de 1 s: lê o sensor e entrega a leitura. Com pausa, o sensor nem é chamado."""

import logging
from collections.abc import Callable

from pulso.clock import Clock
from pulso.sensors.base import Sensor, SensorFrame

log = logging.getLogger(__name__)


class SensorLoop:
    def __init__(self, sensor: Sensor, clock: Clock, interval: float = 1.0) -> None:
        self._sensor = sensor
        self._clock = clock
        self._interval = interval
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        """Pausa de privacidade: a partir daqui o sensor não é mais chamado."""
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def tick(self) -> SensorFrame | None:
        """Uma volta do laço. Devolve None se pausado; leitura "desconhecida" se o sensor falhar."""
        if self._paused:
            return None
        try:
            return self._sensor.read()
        except Exception as exc:  # um sensor com defeito não pode derrubar o app
            # Só o tipo do erro vai para o log: a mensagem poderia conter dados do sensor.
            log.warning("falha na leitura do sensor: %s", type(exc).__name__)
            return SensorFrame.unknown()

    def run(self, on_frame: Callable[[SensorFrame], None], max_ticks: int | None = None) -> None:
        """Repete `tick` a cada `interval` s e passa cada leitura a `on_frame` (até `max_ticks`)."""
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            frame = self.tick()
            if frame is not None:
                on_frame(frame)
            ticks += 1
            self._clock.sleep(self._interval)
