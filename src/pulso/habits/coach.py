"""O treinador de hábitos: junta pomodoro, água e banco, e calcula a pendência.

É a única peça que **grava** eventos de hábito. As máquinas de estado (`Pomodoro`, `Water`) só
decidem; o `HabitCoach` anota o que aconteceu em `habit_event` e responde "o pet está nervoso?".

**Pendência (regra, não rede):** cada hábito (água, pausa) soma pontos por recusa (`refuse_points`)
e por omissão (`ignore_points`); "depois" vale 0 e só o "fiz" zera. Com `nervous_at` pontos ou mais
em **qualquer** dos dois, o pet fica nervoso. Como é calculada dos eventos gravados, sobrevive a
fechar o app, e não esfria sozinha com o tempo.
"""

from dataclasses import dataclass

from pulso.clock import Clock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.pomodoro import Pomodoro
from pulso.habits.water import Water
from pulso.storage.db import HabitStore

_SIGNALS = {kinds.SHOW_WATER, kinds.SHOW_BREAK, kinds.SHOW_BACK}  # avisos: não são gravados

# Respostas do dono que a interface pode pedir (nome → método do coach).
ANSWERS = ("drink", "water_later", "water_decline", "rest", "break_later", "break_decline", "skip")


@dataclass(frozen=True)
class HabitTick:
    """O que a volta de 1 s trouxe: o que foi gravado e o que a interface deve avisar."""

    recorded: tuple[str, ...] = ()
    shown: tuple[str, ...] = ()  # `SHOW_WATER`, `SHOW_BREAK`, `SHOW_BACK`


class HabitCoach:
    def __init__(self, clock: Clock, store: HabitStore, cfg: HabitConfig | None = None) -> None:
        self.cfg = cfg or HabitConfig()
        self.store = store
        self.pomodoro = Pomodoro(clock, self.cfg)
        self.water = Water(clock, self.cfg)
        self._pending: dict[str, int] | None = None  # cache; zera a cada evento gravado

    # ---- relógio -----------------------------------------------------------------------------

    def tick(self, presence: Presence) -> HabitTick:
        events = self.water.tick(presence) + self.pomodoro.tick(presence)
        return self._handle(events)

    # ---- respostas do dono -------------------------------------------------------------------

    def answer(self, action: str) -> str | None:
        """Executa uma resposta de `ANSWERS` e devolve o `kind` gravado (ou `None`)."""
        if action not in ANSWERS:
            raise ValueError(f"resposta desconhecida: {action!r}")
        kind = getattr(self, action)()
        if kind is not None:
            self._handle([kind])
        return kind

    def drink(self) -> str:
        return self.water.drink()

    def water_later(self) -> str | None:
        return self.water.later()

    def water_decline(self) -> str | None:
        return self.water.decline()

    def rest(self) -> str | None:
        return self.pomodoro.rest()

    def break_later(self) -> str | None:
        return self.pomodoro.later()

    def break_decline(self) -> str | None:
        return self.pomodoro.decline()

    def skip(self) -> str | None:
        return self.pomodoro.skip()

    # ---- consulta ----------------------------------------------------------------------------

    @property
    def asking(self) -> str | None:
        """Qual lembrete espera resposta: `"water"`, `"break"` ou `None` (água primeiro)."""
        if self.water.asking:
            return "water"
        if self.pomodoro.asking:
            return "break"
        return None

    def pending(self, group: str) -> int:
        """Pontos de pendência de `"water"` ou `"break"`."""
        if self._pending is None:
            self._pending = {
                g: self.store.pending(g, self.cfg.refuse_points, self.cfg.ignore_points)
                for g in ("water", "break")
            }
        return self._pending[group]

    @property
    def nervous(self) -> bool:
        return self.nervous_reason is not None

    @property
    def nervous_reason(self) -> str | None:
        """O motivo do nervoso, em palavras ("água", "pausa", "água e pausa"), ou `None`."""
        late = [
            name
            for group, name in (("water", "água"), ("break", "pausa"))
            if self.pending(group) >= self.cfg.nervous_at
        ]
        return " e ".join(late) if late else None

    def cups_today(self) -> int:
        return self.store.count_today(kinds.WATER_DRUNK)

    def pomodoros_today(self) -> int:
        return self.store.count_today(kinds.FOCUS_DONE)

    # ---- interno -----------------------------------------------------------------------------

    def _handle(self, events: list[str]) -> HabitTick:
        recorded = [e for e in events if e not in _SIGNALS]
        for kind in recorded:
            self.store.record(kind)
        if recorded:
            self._pending = None
        return HabitTick(tuple(recorded), tuple(e for e in events if e in _SIGNALS))
