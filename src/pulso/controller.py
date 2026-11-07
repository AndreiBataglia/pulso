"""O cérebro do app sem Qt: junta sensor, rede, decodificador, regras de recompensa e gravação.

A interface só chama este objeto (uma vez por segundo `tick`, e os botões). Assim toda a lógica de
"o que acontece a cada segundo" é testada sem abrir janela.

O laço de 1 s (plano da etapa 4): ler o sensor → `engine.step(encode(frame), 100)` →
`decoder.update(counts)` → `saver.tick()`. A decisão da rede (lembrar × esperar) é lida por
`tick_habits`, que a passa ao ciclo do foco.

Os hábitos (ciclo do foco e água) andam em paralelo, por `tick_habits()`, que roda **também com a
observação pausada**. O ciclo do foco mede a presença pela ociosidade lida do sensor; com a
observação pausada ele **congela** (sem leitura, sem presença), e a água segue. O sensor de
reunião (microfone em uso) só é lido com a observação ligada. A pausa corta o sensor e o
aprendizado (a rede não recebe recompensa de hábito enquanto o Pulso "dorme").
"""

import logging
import time
from collections import deque
from dataclasses import dataclass

import numpy as np

from pulso.brain.decoding import MoodDecoder
from pulso.brain.encoding import encode
from pulso.brain.engine import BrainSnapshot, Engine
from pulso.brain.numpy_engine import REMIND
from pulso.brain.rewards import RewardRules
from pulso.clock import Clock
from pulso.habits import kinds, mood_rules
from pulso.habits.coach import HabitCoach, HabitTick
from pulso.habits.focus_cycle import Mode
from pulso.habits.kinds import Presence
from pulso.loop import SensorLoop
from pulso.sensors.base import Sensor
from pulso.sensors.meeting import MeetingSensor
from pulso.storage.brain_store import AutoSaver

log = logging.getLogger(__name__)

STEP_MS = 100  # tempo simulado da rede por volta do laço (1 passo = 1 ms; ver numpy_engine)
DOPAMINE_LOG_SIZE = 200  # quantas entregas de dopamina ficam na lembrança dos gráficos


# Respostas ao lembrete da pausa: as que a rede aprende como decisão de lembrar ou esperar.
_REMINDER_ANSWERS = (
    kinds.BREAK_ACCEPTED,
    kinds.BREAK_SNOOZED,
    kinds.BREAK_DECLINED,
    kinds.BREAK_IGNORED,
)


@dataclass(frozen=True)
class DopamineEvent:
    """Uma entrega de dopamina, para o gráfico: quando (relógio real), quanto e de quem."""

    time: float
    value: float  # d = r − r̄
    source: str  # "dono" (Carinho/Bronca) ou "regra" (recompensa automática)


@dataclass(frozen=True)
class TickResult:
    """O que mudou nesta volta. Não carrega nenhum dado de sensor (privacidade)."""

    mood: str | None  # a decisão atual da rede: "lembrar" ou "esperar" (None antes da 1ª)
    mood_changed: (
        bool  # a rede decidiu diferente nesta volta (de lembrar para esperar, ou o inverso)
    )


class PetController:
    def __init__(
        self,
        sensor: Sensor,
        clock: Clock,
        engine: Engine,
        decoder: MoodDecoder,
        rules: RewardRules,
        saver: AutoSaver,
        habits: HabitCoach,
        meeting: MeetingSensor | None = None,
    ) -> None:
        self._loop = SensorLoop(sensor, clock)
        self._engine = engine
        self._decoder = decoder
        self._rules = rules
        self._saver = saver
        self._clock = clock
        self.habits = habits
        self._meeting = meeting  # None = sem sensor de reunião (testes, outros sistemas)
        self._presence = Presence.UNKNOWN  # só um rótulo (presente/longe/?), nada do sensor
        self._idle: float | None = None  # segundos sem entrada nesta volta (None = sem leitura)
        self.dopamine_events: deque[DopamineEvent] = deque(maxlen=DOPAMINE_LOG_SIZE)
        self.step_cost_ms = 0.0  # custo medido de 1 volta (100 passos de rede), em ms reais

    @property
    def paused(self) -> bool:
        return self._loop.paused

    @property
    def mood(self) -> str | None:
        return self._decoder.mood

    @property
    def wants_to_remind(self) -> bool:
        """A rede decidiu que é boa hora de lembrar da pausa? Antes da 1ª decisão, sim."""
        return self._decoder.mood in (None, REMIND)

    @property
    def verdict(self) -> mood_rules.MoodVerdict:
        """O humor do rosto e o porquê, por regras claras (`habits/mood_rules.py`). A rede não
        escolhe a cara: ela decide o momento do lembrete."""
        habits = self.habits
        return mood_rules.decide(
            mood_rules.MoodInputs(
                nervous_reason=habits.nervous_reason,
                postponements=habits.cycle.postponements,
                idle_s=self._idle,
                sleepy_after_s=habits.cfg.away_idle_s,
                on_time_breaks=habits.on_time_breaks_today(),
                cups=habits.cups_today(),
            )
        )

    @property
    def shown_mood(self) -> str:
        """O humor que o rosto mostra agora."""
        return self.verdict.mood

    def tick(self) -> TickResult | None:
        """Uma volta de 1 s. Pausado → `None`: não lê o sensor, não simula, não aprende."""
        frame = self._loop.tick()
        self._presence = self._presence_of(frame)
        self._idle = frame.idle_seconds if frame is not None and frame.valid else None
        if frame is None:
            return None
        before = self._decoder.mood
        started = time.perf_counter()
        counts = self._engine.step(encode(frame), STEP_MS).counts
        self.step_cost_ms = (time.perf_counter() - started) * 1000.0
        self._decoder.update(counts)
        mood = self._decoder.mood
        self._saver.tick()
        return TickResult(mood, before is not None and mood != before)

    def owner_reward(self, sign: int) -> bool:
        """Carinho (`sign` > 0) ou bronca (`sign` < 0). Devolve False se o clique foi ignorado
        (repetido em poucos segundos) ou se o Pulso está pausado."""
        if self.paused:
            return False
        value = self._rules.owner(sign)
        if value == 0.0:
            return False
        self._deliver(value, "dono")
        return True

    def _presence_of(self, frame) -> Presence:
        if frame is None or not frame.valid:
            return Presence.UNKNOWN
        away = frame.idle_seconds >= self.habits.cfg.away_idle_s
        return Presence.AWAY if away else Presence.PRESENT

    # ---- hábitos -----------------------------------------------------------------------------

    def tick_habits(self) -> HabitTick:
        """Anda o ciclo do foco e a água (também pausado) e recompensa o que foi gravado."""
        meeting = (
            self._meeting is not None and self._idle is not None and self._meeting.in_meeting()
        )
        forced = self.habits.cycle.reminder_forced
        tick = self.habits.tick(self._presence, self._idle, meeting, self.wants_to_remind)
        self._reward_habits(tick.rewarded, forced)
        return tick

    def answer_habit(self, action: str) -> HabitTick:
        """Resposta do dono a uma pergunta (`habits.coach.ANSWERS`). Devolve o que foi gravado
        (vazio quando a resposta não grava nada, como "Pausar agora")."""
        forced = self.habits.cycle.reminder_forced
        tick = self.habits.answer(action)
        self._reward_habits(tick.rewarded, forced)
        return tick

    def set_mode(self, mode: Mode) -> None:
        """Modo profissional ou casual (a pílula da janela e a bandeja)."""
        self.habits.set_mode(mode)

    def _reward_habits(self, recorded, forced: bool = False) -> None:
        """`forced`: o lembrete tocou pelo teto de tempo, com a rede dizendo "esperar". Aí a
        resposta vale ao contrário: aceitar mostra que esperar foi erro; recusar, que foi acerto."""
        if self.paused:  # o Pulso "dorme": o evento fica anotado, mas a rede não aprende nada
            return
        for kind in recorded:
            value = self._rules.habit(kind, self.habits.cycle.postponements)
            if forced and kind in _REMINDER_ANSWERS:
                value = -value
            if value != 0.0:
                self._deliver(value, "regra")  # hábito é regra, não rede: mesma cor na aba Cérebro

    def _deliver(self, value: float, source: str) -> None:
        dopamine = self._engine.reward(value)
        self.dopamine_events.append(DopamineEvent(self._clock.now(), dopamine, source))

    # ---- para a aba Cérebro (só leitura) ------------------------------------------------------

    def snapshot(self) -> BrainSnapshot:
        """Fotografia da rede para os gráficos (copias; não mexe na rede)."""
        return self._engine.snapshot()

    def mood_counts(self) -> np.ndarray:
        """Pulsos de cada humor na última janela de decisão (a que o decodificador usou)."""
        return self._decoder.counts()

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
