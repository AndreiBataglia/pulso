"""Neurônios LIF (*leaky integrate-and-fire*): acumulam carga, vazam e disparam ao passar do limiar.

A equação, com o tempo em passos de `dt` = 1 ms (método de Euler):

    V  ←  V + (dt / τm) · (V_repouso − V + drive)  +  saltos_sinápticos

- O termo `(V_repouso − V)` é o **vazamento**: sem estímulo, V volta sozinho para o repouso.
- `drive` é um empurrão constante (em mV de "tensão equivalente"), para testar um neurônio isolado.
- `saltos_sinápticos` é a soma dos pesos dos pulsos que chegaram neste passo (sinapse instantânea:
  cada pulso empurra V de uma vez, pelo valor do peso em mV).
- Se V ≥ limiar, o neurônio **dispara**, V volta ao `v_reset_mv` e ele fica surdo durante o período
  **refratário** (`t_ref_ms`).
"""

from dataclasses import dataclass

import numpy as np

DT_MS = 1.0  # passo da simulação (TRD §5.1)


@dataclass(frozen=True)
class LIFParams:
    tau_m_ms: float = 20.0  # constante de tempo da membrana: quão devagar ela vaza
    v_rest_mv: float = -65.0
    v_threshold_mv: float = -50.0
    v_reset_mv: float = -65.0
    t_ref_ms: float = 2.0  # período refratário


class LIFPopulation:
    """Um grupo de `n` neurônios LIF simulados juntos (vetorizado em numpy)."""

    def __init__(self, n: int, params: LIFParams | None = None) -> None:
        self.params = params or LIFParams()
        self.n = n
        self.v = np.full(n, self.params.v_rest_mv)
        # Passos que ainda faltam de refratário, por neurônio.
        self._refractory_steps = np.zeros(n, dtype=int)
        self._ref_steps_on_spike = round(self.params.t_ref_ms / DT_MS)

    def reset(self) -> None:
        self.v[:] = self.params.v_rest_mv
        self._refractory_steps[:] = 0

    def step(self, synaptic_mv: np.ndarray, drive_mv: float = 0.0) -> np.ndarray:
        """Avança 1 passo. Devolve um vetor de bool: quem disparou neste passo."""
        p = self.params
        ready = self._refractory_steps <= 0  # neurônio refratário não integra nada
        leak = (DT_MS / p.tau_m_ms) * (p.v_rest_mv - self.v + drive_mv)
        v_new = self.v + leak + synaptic_mv
        self.v = np.where(ready, v_new, p.v_reset_mv)
        self._refractory_steps = np.maximum(self._refractory_steps - 1, 0)

        spikes = ready & (self.v >= p.v_threshold_mv)
        self.v[spikes] = p.v_reset_mv
        self._refractory_steps[spikes] = self._ref_steps_on_spike
        return spikes
