"""Recompensas: regras automáticas e carinho/bronca do dono → o valor que vira dopamina.

Duas fontes, que somam:

- **Dono:** 💚 Carinho (+1) e 💢 Bronca (−1), multiplicados por `owner_weight`.
- **Regras automáticas** (o comportamento mínimo desde o primeiro dia, multiplicadas por
  `rules_weight`, menor que o do dono: o dono sempre pesa mais):
  - ócio longo e o pet está **sonolento** → +;
  - o dono **volta** do ócio e o pet está **animado** → +;
  - mais de 90 min **sem pausa** e o pet está **preocupado** → +.

Cada regra tem um intervalo mínimo entre disparos (`cooldown_s`), senão ela "gritaria" a cada
segundo em que a condição continua valendo. Cliques repetidos do dono em poucos segundos também são
ignorados (`click_filter_s`): quem clica 5 vezes seguidas por impaciência vale como um clique.

O tempo vem de um `Clock` injetado (nunca `time.time()`), então os testes controlam as horas.
"""

from dataclasses import dataclass

from pulso.clock import Clock
from pulso.sensors.base import SensorFrame


@dataclass(frozen=True)
class RewardConfig:
    owner_weight: float = 1.0
    rules_weight: float = 0.3
    long_idle_s: float = 300.0  # 5 min parado já conta como "ócio longo"
    returned_window_s: float = 60.0  # por quanto tempo a "volta" pode ser premiada
    no_break_s: float = 90 * 60.0  # 90 min sem pausa
    break_idle_s: float = 300.0  # ficar parado 5 min conta como pausa
    cooldown_s: float = 10.0  # intervalo mínimo entre dois disparos da mesma regra
    click_filter_s: float = 3.0  # cliques do dono mais próximos que isto são ignorados


class RewardRules:
    def __init__(self, clock: Clock, config: RewardConfig | None = None) -> None:
        self._clock = clock
        self.cfg = config or RewardConfig()
        self._last_click: float | None = None
        self._last_fire: dict[str, float] = {}
        self._was_long_idle = False
        self._returned_at: float | None = None
        self._active_since: float | None = None  # início do trabalho contínuo atual

    # ---- dono --------------------------------------------------------------------------------

    def owner(self, sign: int) -> float:
        """Carinho (`sign` > 0) ou bronca (`sign` < 0). Devolve o valor, ou 0.0 se repetido."""
        now = self._clock.now()
        if self._last_click is not None and now - self._last_click < self.cfg.click_filter_s:
            return 0.0
        self._last_click = now
        return (1.0 if sign > 0 else -1.0) * self.cfg.owner_weight

    # ---- regras automáticas ------------------------------------------------------------------

    def evaluate(self, frame: SensorFrame, mood: str | None) -> float:
        """Chamado a cada leitura. Devolve a recompensa automática desta volta (0.0 na maioria)."""
        if not frame.valid:  # leitura falhou: nada a concluir
            return 0.0
        now = self._clock.now()
        c = self.cfg
        long_idle = frame.idle_seconds >= c.long_idle_s

        # Volta do ócio: estava parado e agora mexeu.
        if self._was_long_idle and not long_idle:
            self._returned_at = now
        self._was_long_idle = long_idle

        # Trabalho contínuo: zera quando o dono fica parado tempo suficiente para valer como pausa.
        if frame.idle_seconds >= c.break_idle_s:
            self._active_since = None
        elif self._active_since is None:
            self._active_since = now

        total = 0.0
        if long_idle and mood == "sonolento":
            total += self._fire("idle_sleepy", now)
        returned = self._returned_at is not None and now - self._returned_at <= c.returned_window_s
        if returned and mood == "animado":
            total += self._fire("back_cheerful", now)
        worked = self._active_since is not None and now - self._active_since >= c.no_break_s
        if worked and mood == "preocupado":
            total += self._fire("no_break_worried", now)
        return total * c.rules_weight

    def _fire(self, rule: str, now: float) -> float:
        """1.0 se a regra pode disparar agora (respeitando o intervalo mínimo), senão 0.0."""
        last = self._last_fire.get(rule)
        if last is not None and now - last < self.cfg.cooldown_s:
            return 0.0
        self._last_fire[rule] = now
        return 1.0
