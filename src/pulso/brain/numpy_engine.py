"""Motor da rede de pulso em numpy puro: entrada de Poisson → camada oculta → camada de saída.

    entrada (Poisson) ──► oculta: 80 excitatórios + 20 inibitórios ──► saída: 5 grupos × 10
                              (LIF, conexões esparsas ~20%)               (LIF, inibição lateral)

- **Entrada:** não são neurônios LIF, são geradores de Poisson. Cada um dispara ao acaso, com
  probabilidade `taxa · dt` a cada passo (uma taxa de 100 Hz = 10% de chance por milissegundo).
- **Oculta:** neurônios excitatórios empurram V para cima; os inibitórios empurram para baixo. Isso
  segura a atividade (sem eles, a rede tende a disparar toda de uma vez).
- **Saída:** um grupo por humor. A **inibição lateral** faz cada grupo calar os outros: quem dispara
  mais "ganha" e abafa os demais (competição *winner-take-all*).
- **Atraso de um passo:** o pulso disparado no passo t só chega aos vizinhos no passo t+1.

Nesta etapa os pesos são sorteados (semente fixa) e não mudam: a rede pulsa, mas ainda não aprende.
"""

from dataclasses import dataclass

import numpy as np

from pulso.brain.engine import StepResult
from pulso.brain.lif import DT_MS, LIFParams, LIFPopulation

DEFAULT_GROUPS = ("animado", "contente", "entediado", "sonolento", "preocupado")


@dataclass(frozen=True)
class NetworkConfig:
    """Tamanho da rede e força das sinapses (pesos em mV: o salto que um pulso dá em V)."""

    n_inputs: int = 63  # deve casar com `encoding.N_INPUTS` (há um teste para isso)
    groups: tuple[str, ...] = DEFAULT_GROUPS
    group_size: int = 10  # neurônios de saída por humor
    n_hidden_e: int = 80
    n_hidden_i: int = 20
    p_connect: float = 0.2  # chance de existir cada conexão (esparsidade)
    w_in_max_mv: float = 4.0  # entrada → oculta (sorteio uniforme em [0, máx])
    w_ee_max_mv: float = 0.5  # excitatório → oculta
    w_inh_max_mv: float = 3.0  # inibitório → oculta (aplicado com sinal negativo)
    w_out_max_mv: float = 4.0  # oculta excitatória → saída
    w_lateral_mv: float = 3.0  # inibição lateral entre grupos de saída (sinal negativo)


class NumpyEngine:
    def __init__(self, seed: int = 0, config: NetworkConfig | None = None) -> None:
        self.config = cfg = config or NetworkConfig()
        self.n_inputs = cfg.n_inputs
        self.groups = list(cfg.groups)
        self._n_hidden = cfg.n_hidden_e + cfg.n_hidden_i
        self._n_out = len(cfg.groups) * cfg.group_size
        self._rng = np.random.default_rng(seed)

        self.hidden = LIFPopulation(self._n_hidden, LIFParams())
        self.output = LIFPopulation(self._n_out, LIFParams())
        self._build_weights()
        # Pulsos do passo anterior (chegam aos vizinhos só no passo seguinte).
        self._hidden_spikes = np.zeros(self._n_hidden)
        self._out_spikes = np.zeros(self._n_out)

    # ---- construção ----------------------------------------------------------------------

    def _sparse(self, shape: tuple[int, int], w_max: float) -> np.ndarray:
        """Pesos sorteados em [0, w_max]; só `p_connect` das conexões existem (o resto vale 0)."""
        exists = self._rng.random(shape) < self.config.p_connect
        return exists * self._rng.uniform(0.0, w_max, shape)

    def _build_weights(self) -> None:
        cfg = self.config
        n_e, n_h, n_o = cfg.n_hidden_e, self._n_hidden, self._n_out
        # Convenção: w[pré, pós]. Os n_e primeiros neurônios ocultos são excitatórios; o resto,
        # inibitório.
        self.w_in_hidden = self._sparse((cfg.n_inputs, n_h), cfg.w_in_max_mv)

        w_hh = np.zeros((n_h, n_h))
        w_hh[:n_e] = self._sparse((n_e, n_h), cfg.w_ee_max_mv)
        w_hh[n_e:] = -self._sparse((n_h - n_e, n_h), cfg.w_inh_max_mv)
        np.fill_diagonal(w_hh, 0.0)  # neurônio não faz sinapse em si mesmo
        self.w_hidden_hidden = w_hh

        w_ho = np.zeros((n_h, n_o))
        # Só os excitatórios falam com a saída.
        w_ho[:n_e] = self._sparse((n_e, n_o), cfg.w_out_max_mv)
        self.w_hidden_out = w_ho

        # Inibição lateral: cada neurônio de saída inibe os de OUTROS grupos (nunca os do próprio).
        group_of = np.repeat(np.arange(len(cfg.groups)), cfg.group_size)
        self.w_out_out = -cfg.w_lateral_mv * (group_of[:, None] != group_of[None, :])

    # ---- simulação -----------------------------------------------------------------------

    def step(self, rates_hz: np.ndarray, duration_ms: int) -> StepResult:
        rates = np.asarray(rates_hz, dtype=float)
        if rates.shape != (self.n_inputs,):
            raise ValueError(f"esperava {self.n_inputs} taxas de entrada, recebi {rates.shape}")

        # Todos os pulsos de Poisson do trecho de uma vez: uma linha por milissegundo.
        input_spikes = self._rng.random((duration_ms, self.n_inputs)) < rates * (DT_MS / 1000.0)

        out_total = np.zeros(self._n_out)
        hidden_total = 0
        for in_spk in input_spikes:
            syn_hidden = in_spk @ self.w_in_hidden + self._hidden_spikes @ self.w_hidden_hidden
            syn_out = self._hidden_spikes @ self.w_hidden_out + self._out_spikes @ self.w_out_out
            self._hidden_spikes = self.hidden.step(syn_hidden).astype(float)
            self._out_spikes = self.output.step(syn_out).astype(float)
            hidden_total += int(self._hidden_spikes.sum())
            out_total += self._out_spikes

        counts = out_total.reshape(len(self.groups), self.config.group_size).sum(axis=1)
        return StepResult(counts=counts.astype(int), hidden_spikes=hidden_total)

    # ---- salvar e restaurar --------------------------------------------------------------

    _WEIGHT_NAMES = ("w_in_hidden", "w_hidden_hidden", "w_hidden_out", "w_out_out")

    def state_dict(self) -> dict[str, np.ndarray]:
        return {name: getattr(self, name).copy() for name in self._WEIGHT_NAMES}

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        # Valida tudo ANTES de trocar qualquer peso: um estado ruim não deixa a rede pela metade.
        for name in self._WEIGHT_NAMES:
            if name not in state:
                raise ValueError(f"estado sem o campo {name!r}")
            if np.shape(state[name]) != getattr(self, name).shape:
                shape = np.shape(state[name])
                raise ValueError(f"campo {name!r} com formato incompatível: {shape}")
        for name in self._WEIGHT_NAMES:
            setattr(self, name, np.array(state[name], dtype=float))
