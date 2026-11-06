"""O treinador de hábitos: junta o ciclo do foco, a água e o banco, e calcula a pendência.

É a única peça que **grava** eventos de hábito. As máquinas de estado (`FocusCycle`, `Water`) só
decidem; o `HabitCoach` anota o que aconteceu em `habit_event` (com o resumo das pausas) e responde
"o Pulso está nervoso?".

**Pendência (regra, não rede):** cada hábito (água, pausa) soma pontos por recusa (`refuse_points`)
e por omissão (`ignore_points`); "depois" vale 0 e só o "fiz" zera. Com `nervous_at` pontos ou mais
em **qualquer** dos dois, o Pulso fica nervoso. Como é calculada dos eventos gravados, sobrevive a
fechar o app, e não esfria sozinha com o tempo.
"""

from dataclasses import dataclass

from pulso.clock import Clock
from pulso.habits import kinds
from pulso.habits.focus_cycle import AwayAnswer, CycleEvent, FocusCycle, Mode, Phase
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.water import Water
from pulso.storage.db import HabitStore

# Avisos para a interface: não são gravados.
_SIGNALS = {kinds.SHOW_WATER, kinds.SHOW_BREAK, kinds.SHOW_BACK, kinds.SHOW_ASK_BACK}

# Respostas do dono que a interface pode pedir (nome → método do coach).
ANSWERS = (
    "drink", "water_later", "water_decline",
    "take_break", "postpone", "break_decline", "end_break_early", "skip",
    "away_pause", "away_meal", "away_need", "away_focus",
)  # fmt: skip


@dataclass(frozen=True)
class HabitTick:
    """O que a volta de 1 s trouxe: o que foi gravado e o que a interface deve avisar."""

    recorded: tuple[str, ...] = ()
    shown: tuple[str, ...] = ()  # `SHOW_WATER`, `SHOW_BREAK`, `SHOW_BACK`, `SHOW_ASK_BACK`
    rewarded: tuple[str, ...] = ()  # dos gravados, os que a rede aprende (refeição não entra)
    summary: CycleEvent | None = None  # o resumo da pausa que acabou de terminar, se houve


class HabitCoach:
    def __init__(
        self,
        clock: Clock,
        store: HabitStore,
        cfg: HabitConfig | None = None,
        mode: Mode = Mode.PROFESSIONAL,
    ) -> None:
        self.cfg = cfg or HabitConfig()
        self.store = store
        self.cycle = FocusCycle(clock, self.cfg, mode)
        self.water = Water(clock, self.cfg)
        self._pending: dict[str, int] | None = None  # cache; zera a cada evento gravado

    def apply_config(self, cfg: HabitConfig) -> None:
        """Troca os tempos sem reiniciar (a tela de Ajustes)."""
        self.cfg = cfg
        self.cycle.set_config(cfg)
        self.water.set_config(cfg)

    @property
    def mode(self) -> Mode:
        return self.cycle.mode

    def set_mode(self, mode: Mode) -> None:
        self.cycle.set_mode(mode)

    # ---- relógio -----------------------------------------------------------------------------

    def tick(
        self, presence: Presence, idle_s: float | None = None, meeting: bool = False
    ) -> HabitTick:
        """Uma volta. `idle_s` = segundos sem teclado nem mouse (`None` = observação pausada: o
        ciclo congela); `meeting` = microfone em uso por outro programa."""
        events = [CycleEvent(kind) for kind in self.water.tick(presence)]
        events += self.cycle.tick(idle_s, meeting)
        return self._handle(events)

    # ---- respostas do dono -------------------------------------------------------------------

    def answer(self, action: str) -> HabitTick:
        """Executa uma resposta de `ANSWERS` e devolve o que foi gravado."""
        if action not in ANSWERS:
            raise ValueError(f"resposta desconhecida: {action!r}")
        result = getattr(self, action)()
        if isinstance(result, str):
            events = [CycleEvent(result)]
        else:
            events = list(result or [])
        return self._handle(events)

    def drink(self) -> str:
        return self.water.drink()

    def water_later(self) -> str | None:
        return self.water.later()

    def water_decline(self) -> str | None:
        return self.water.decline()

    def take_break(self) -> list[CycleEvent]:
        """ "Pausar agora": começa o descanso. O que vale ponto é a pausa **concluída**."""
        self.cycle.take_break()
        return []

    def postpone(self) -> list[CycleEvent]:
        return self.cycle.postpone()

    def break_decline(self) -> list[CycleEvent]:
        return self.cycle.decline()

    def end_break_early(self) -> list[CycleEvent]:
        return self.cycle.end_break_early()

    def skip(self) -> list[CycleEvent]:
        return self.cycle.skip()

    def away_pause(self) -> list[CycleEvent]:
        return self.cycle.answer_back(AwayAnswer.PAUSE)

    def away_meal(self) -> list[CycleEvent]:
        return self.cycle.answer_back(AwayAnswer.MEAL)

    def away_need(self) -> list[CycleEvent]:
        return self.cycle.answer_back(AwayAnswer.NEED)

    def away_focus(self) -> list[CycleEvent]:
        return self.cycle.answer_back(AwayAnswer.FOCUS)

    # ---- consulta ----------------------------------------------------------------------------

    @property
    def asking(self) -> str | None:
        """Qual pergunta espera resposta: `"away"` (o que foi?), `"break"` (lembrete de pausa),
        `"water"` ou `None`. A do ciclo vem antes: a água espera a vez no painel."""
        if self.cycle.phase is Phase.ASKING_BACK:
            return "away"
        if self.cycle.phase is Phase.REMINDER:
            return "break"
        if self.water.asking:
            return "water"
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
        """Focos concluídos hoje."""
        return self.store.count_today(kinds.FOCUS_DONE)

    def breaks_today(self) -> int:
        return self.store.count_today(kinds.BREAK_DONE)

    def postponed_today(self) -> int:
        return self.store.count_today(kinds.BREAK_SNOOZED)

    # ---- interno -----------------------------------------------------------------------------

    def _handle(self, events: list[CycleEvent]) -> HabitTick:
        recorded = [e for e in events if e.kind not in _SIGNALS]
        for e in recorded:
            self.store.record(e.kind, e.value, e.category, e.planned_s, e.actual_s, e.excess_s)
        if recorded:
            self._pending = None
        # Refeição conta como descanso longo, mas a rede só aprende com pausa e foco.
        rewarded = tuple(e.kind for e in recorded if e.category != kinds.CAT_MEAL)
        summary = next((e for e in recorded if e.kind == kinds.BREAK_DONE), None)
        return HabitTick(
            tuple(e.kind for e in recorded),
            tuple(e.kind for e in events if e.kind in _SIGNALS),
            rewarded,
            summary,
        )
