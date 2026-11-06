"""Um lembrete que pergunta e espera resposta: a peça comum da água e do descanso.

Ciclo: **armado** (espera `due_in` segundos) → **mostrado** (o dono vê o balão) → respondido
(fiz / depois / recusei) ou **ignorado** (5 min mostrado sem resposta). Duas regras de presença:

- Chegou a hora e o dono está **longe** do PC: o lembrete espera a volta (não aparece para ninguém).
- O relógio do "ignorei" só anda com o dono **presente** e a observação ligada. Longe ou com a
  observação pausada não se sabe se ele viu, então não se pode acusá-lo de ignorar.

O tempo vem de um `Clock` injetado, como no resto do projeto: os testes controlam as horas.
"""

from pulso.clock import Clock
from pulso.habits.kinds import Presence


class Reminder:
    def __init__(self, clock: Clock, ignore_after_s: float) -> None:
        self._clock = clock
        self._ignore_after_s = ignore_after_s
        self._due_at: float | None = None  # None = desarmado
        self._shown = False
        self._unanswered_s = 0.0  # tempo mostrado, com o dono presente, sem resposta
        self._last = clock.now()

    @property
    def armed(self) -> bool:
        return self._due_at is not None

    @property
    def shown(self) -> bool:
        """O balão está na tela esperando resposta?"""
        return self._shown

    @property
    def remaining_s(self) -> float | None:
        """Segundos até aparecer (0 se já está na tela); `None` se desarmado."""
        if self._due_at is None:
            return None
        return max(self._due_at - self._clock.now(), 0.0)

    def arm(self, due_in_s: float) -> None:
        """(Re)arma para daqui a `due_in_s` segundos e some com o balão, se havia um."""
        self._due_at = self._clock.now() + due_in_s
        self._shown = False
        self._unanswered_s = 0.0
        self._last = self._clock.now()

    def disarm(self) -> None:
        self._due_at = None
        self._shown = False
        self._unanswered_s = 0.0

    def tick(self, presence: Presence) -> str | None:
        """Anda o relógio. Devolve `"shown"` (acabou de aparecer) ou `"ignored"`, senão `None`."""
        now = self._clock.now()
        elapsed, self._last = now - self._last, now
        if self._due_at is None:
            return None
        if not self._shown:
            if now >= self._due_at and presence is not Presence.AWAY:
                self._shown = True
                self._unanswered_s = 0.0
                return "shown"
            return None
        if presence is Presence.PRESENT:
            self._unanswered_s += elapsed
            if self._unanswered_s >= self._ignore_after_s:
                self.disarm()
                return "ignored"
        return None
