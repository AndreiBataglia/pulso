"""O cérebro do app sem Qt: junta sensor, rede, decodificador, regras de recompensa e gravação.

A interface só chama este objeto (uma vez por segundo `tick`, e os botões). Assim toda a lógica de
"o que acontece a cada segundo" é testada sem abrir janela.

O laço de 1 s (plano da etapa 4): ler o sensor → `engine.step(encode(frame), 100)` →
`decoder.update(counts)` → `rules.evaluate(frame, humor)` (se > 0, `engine.reward`) →
`saver.tick()`.
"""

import logging
from dataclasses import dataclass

from pulso.brain.decoding import MoodDecoder
from pulso.brain.encoding import encode
from pulso.brain.engine import Engine
from pulso.brain.rewards import RewardRules
from pulso.clock import Clock
from pulso.loop import SensorLoop
from pulso.sensors.base import Sensor
from pulso.storage.brain_store import AutoSaver

log = logging.getLogger(__name__)

STEP_MS = 100  # tempo simulado da rede por volta do laço (1 passo = 1 ms; ver numpy_engine)


@dataclass(frozen=True)
class TickResult:
    """O que mudou nesta volta. Não carrega nenhum dado de sensor (privacidade)."""

    mood: str | None  # humor atual (None até a primeira decisão)
    mood_changed: bool  # a rede decidiu um humor diferente nesta volta
    rewarded: float  # recompensa automática aplicada (0.0 na maioria das voltas)


class PetController:
    def __init__(
        self,
        sensor: Sensor,
        clock: Clock,
        engine: Engine,
        decoder: MoodDecoder,
        rules: RewardRules,
        saver: AutoSaver,
    ) -> None:
        self._loop = SensorLoop(sensor, clock)
        self._engine = engine
        self._decoder = decoder
        self._rules = rules
        self._saver = saver

    @property
    def paused(self) -> bool:
        return self._loop.paused

    @property
    def mood(self) -> str | None:
        return self._decoder.mood

    def tick(self) -> TickResult | None:
        """Uma volta de 1 s. Pausado → `None`: não lê o sensor, não simula, não aprende."""
        frame = self._loop.tick()
        if frame is None:
            return None
        before = self._decoder.mood
        counts = self._engine.step(encode(frame), STEP_MS).counts
        self._decoder.update(counts)
        mood = self._decoder.mood
        reward = self._rules.evaluate(frame, mood)
        if reward > 0:
            self._engine.reward(reward)
        self._saver.tick()
        return TickResult(mood, before is not None and mood != before, reward)

    def owner_reward(self, sign: int) -> bool:
        """Carinho (`sign` > 0) ou bronca (`sign` < 0). Devolve False se o clique foi ignorado
        (repetido em poucos segundos) ou se o pet está pausado."""
        if self.paused:
            return False
        value = self._rules.owner(sign)
        if value == 0.0:
            return False
        self._engine.reward(value)
        return True

    def pause(self) -> None:
        """Pausa de privacidade: para o sensor e guarda o que a rede aprendeu."""
        if not self.paused:
            self._loop.pause()
            self._saver.flush()

    def resume(self) -> None:
        self._loop.resume()

    def shutdown(self) -> None:
        """Ao sair: guarda o cérebro."""
        self._saver.flush()
