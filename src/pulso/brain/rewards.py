"""Recompensas: carinho do dono e respostas aos hábitos → o valor que vira dopamina.

Duas fontes:

- **Dono:** 💚 Carinho (+1) e 💢 Bronca (−1), multiplicados por `owner_weight`. Cliques repetidos em
  poucos segundos são ignorados (`click_filter_s`): quem clica 5 vezes seguidas por impaciência vale
  como um clique.
- **Hábitos:** aceitar o lembrete da pausa / beber água → +; recusar → −; ignorar → − (menor);
  prorrogar → − crescente. Vêm do próprio dono, então pesam como ele (`habit_weight`).

Não há mais regras por processo ou ócio (palpites sobre o humor do dono, que ele nunca confirmava):
a rede só aprende com o que o dono faz de fato. O tempo vem de um `Clock` injetado.
"""

from dataclasses import dataclass

from pulso.clock import Clock
from pulso.habits import kinds

# Hábitos (F07/F08): atendido +, dispensado −. "Depois" e os avisos valem 0. Quem ignora o Pulso
# desagrada menos do que quem o recusa de cara, por isso −0,5 contra −1.
HABIT_VALUES = {
    kinds.WATER_DRUNK: 1.0,
    kinds.BREAK_DONE: 1.0,
    kinds.BREAK_ACCEPTED: 1.0,
    kinds.WATER_DECLINED: -1.0,
    kinds.BREAK_DECLINED: -1.0,
    kinds.WATER_IGNORED: -0.5,
    kinds.BREAK_IGNORED: -0.5,
}

SNOOZE_STEP = 0.25  # cada prorrogação do mesmo lembrete pesa mais 0,25 ...
SNOOZE_MAX_STEPS = 4  # ... até −1,0


@dataclass(frozen=True)
class RewardConfig:
    owner_weight: float = 1.0
    habit_weight: float = 1.0  # hábito é resposta do dono: pesa como carinho e bronca
    click_filter_s: float = 3.0  # cliques do dono mais próximos que isto são ignorados


class RewardRules:
    def __init__(self, clock: Clock, config: RewardConfig | None = None) -> None:
        self._clock = clock
        self.cfg = config or RewardConfig()
        self._last_click: float | None = None

    # ---- dono --------------------------------------------------------------------------------

    def owner(self, sign: int) -> float:
        """Carinho (`sign` > 0) ou bronca (`sign` < 0). Devolve o valor, ou 0.0 se repetido."""
        now = self._clock.now()
        if self._last_click is not None and now - self._last_click < self.cfg.click_filter_s:
            return 0.0
        self._last_click = now
        return (1.0 if sign > 0 else -1.0) * self.cfg.owner_weight

    def habit(self, kind: str, postponements: int = 1) -> float:
        """Recompensa de um evento de hábito (0.0 para os que não contam), com `habit_weight`.

        Prorrogar o lembrete de pausa pesa mais a cada vez (−0,25, −0,5, −0,75, até −1,0, o peso
        de uma recusa); `postponements` é quantas vezes o lembrete atual já foi prorrogado."""
        if kind == kinds.BREAK_SNOOZED:
            value = -SNOOZE_STEP * min(max(postponements, 1), SNOOZE_MAX_STEPS)
        else:
            value = HABIT_VALUES.get(kind, 0.0)
        return value * self.cfg.habit_weight
