"""Lembrete de água (F08): a cada `interval` o pet pede um copo; o dono responde.

Respostas: **bebi** (zera a pendência, soma um copo), **depois** (adia `snooze`), **não quero**
(recusei) e o silêncio (**ignorei**). O botão "Bebi" também vale sem lembrete na tela: o Pulso não
vê o copo, então o dono precisa poder se explicar a qualquer hora. O lembrete é uma **regra**, não
rede neural: é previsível e testável com relógio falso.
"""

from pulso.clock import Clock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.reminder import Reminder


class Water:
    def __init__(self, clock: Clock, cfg: HabitConfig | None = None) -> None:
        self._cfg = cfg or HabitConfig()
        self._reminder = Reminder(clock, self._cfg.ignore_after_min * 60)
        self._reminder.arm(self._cfg.water_interval_min * 60)
        self._enabled = True

    def set_enabled(self, on: bool) -> None:
        """Liga ou desliga o lembrete (preferência do dono). Ligar recomeça um intervalo inteiro."""
        self._enabled = on
        if on:
            self._rearm(self._cfg.water_interval_min)
        else:
            self._reminder.disarm()

    @property
    def asking(self) -> bool:
        """O pet está pedindo água agora?"""
        return self._reminder.shown

    def tick(self, presence: Presence) -> list[str]:
        """Devolve os acontecimentos desta volta: `SHOW_WATER` e/ou `WATER_IGNORED`."""
        outcome = self._reminder.tick(presence)
        if outcome == "shown":
            return [kinds.SHOW_WATER]
        if outcome == "ignored":
            self._rearm(self._cfg.water_interval_min)
            return [kinds.WATER_IGNORED]
        return []

    def drink(self) -> str:
        """Bebi (vale a qualquer hora): o próximo lembrete só daqui a um intervalo inteiro."""
        if self._enabled:
            self._rearm(self._cfg.water_interval_min)
        return kinds.WATER_DRUNK

    def later(self) -> str | None:
        """Depois: adia. Só faz sentido com o balão na tela (senão `None`)."""
        if not self.asking:
            return None
        self._rearm(self._cfg.water_snooze_min)
        return kinds.WATER_SNOOZED

    def decline(self) -> str | None:
        """Não quero: recusa. Só com o balão na tela (senão `None`)."""
        if not self.asking:
            return None
        self._rearm(self._cfg.water_interval_min)
        return kinds.WATER_DECLINED

    def _rearm(self, minutes: float) -> None:
        self._reminder.arm(minutes * 60)
