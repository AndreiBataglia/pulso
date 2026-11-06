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

**Aprendizado (etapa 3):** os pesos entrada→oculta e oculta→saída são plásticos (`plasticity.py`).
A cada passo o STDP alimenta a elegibilidade; o peso só muda quando `reward()` entrega dopamina.
A recorrência da oculta e a inibição lateral são fixas.
"""

from dataclasses import dataclass

import numpy as np

from pulso.brain.engine import StepResult
from pulso.brain.lif import DT_MS, LIFParams, LIFPopulation
from pulso.brain.plasticity import PlasticityConfig, PlasticSynapses

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
    # Só a oculta→saída aprende por padrão. A entrada→oculta fica congelada (eta = 0): nos
    # experimentos da etapa 3, punir essa camada silencia o contexto punido em vez de
    # redirecioná-lo (diário da etapa 3). O mecanismo continua pronto: basta um eta > 0.
    plasticity_in: PlasticityConfig = PlasticityConfig(eta=0.0)
    plasticity_out: PlasticityConfig = PlasticityConfig(eta=0.05)
    baseline_rate: float = 0.1  # quão rápido a média de recompensas r̄ acompanha as recompensas


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
        self._reward_baseline = 0.0  # r̄: média recente das recompensas (dopamina = r − r̄)
        self._stats = np.zeros(3, dtype=np.int64)  # recompensas positivas, negativas, passos
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
        w_in = self._sparse((cfg.n_inputs, n_h), cfg.w_in_max_mv)

        w_hh = np.zeros((n_h, n_h))
        w_hh[:n_e] = self._sparse((n_e, n_h), cfg.w_ee_max_mv)
        w_hh[n_e:] = -self._sparse((n_h - n_e, n_h), cfg.w_inh_max_mv)
        np.fill_diagonal(w_hh, 0.0)  # neurônio não faz sinapse em si mesmo
        self.w_hidden_hidden = w_hh

        w_ho = np.zeros((n_h, n_o))
        # Só os excitatórios falam com a saída.
        w_ho[:n_e] = self._sparse((n_e, n_o), cfg.w_out_max_mv)

        self._in_syn = PlasticSynapses(w_in, w_in > 0, cfg.w_in_max_mv, cfg.plasticity_in)
        self._out_syn = PlasticSynapses(
            w_ho, w_ho > 0, cfg.w_out_max_mv, cfg.plasticity_out, normalize="pre"
        )

        # Inibição lateral: cada neurônio de saída inibe os de OUTROS grupos (nunca os do próprio).
        group_of = np.repeat(np.arange(len(cfg.groups)), cfg.group_size)
        self.w_out_out = -cfg.w_lateral_mv * (group_of[:, None] != group_of[None, :])

    @property
    def w_in_hidden(self) -> np.ndarray:
        return self._in_syn.w

    @property
    def w_hidden_out(self) -> np.ndarray:
        return self._out_syn.w

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
            in_f = in_spk.astype(float)
            delivered_hidden = self._hidden_spikes  # pulsos que chegam à saída NESTE passo
            syn_hidden = in_f @ self.w_in_hidden + delivered_hidden @ self.w_hidden_hidden
            syn_out = delivered_hidden @ self.w_hidden_out + self._out_spikes @ self.w_out_out
            self._hidden_spikes = self.hidden.step(syn_hidden).astype(float)
            self._out_spikes = self.output.step(syn_out).astype(float)
            # STDP: para cada sinapse, "pré" é o pulso que acabou de chegar e "pós" o disparo novo.
            if self._in_syn.cfg.eta > 0:  # camada congelada: nem gasta CPU com rastros
                self._in_syn.update(in_f, self._hidden_spikes)
            self._out_syn.update(delivered_hidden, self._out_spikes)
            hidden_total += int(self._hidden_spikes.sum())
            out_total += self._out_spikes

        self._stats[2] += duration_ms
        counts = out_total.reshape(len(self.groups), self.config.group_size).sum(axis=1)
        return StepResult(counts=counts.astype(int), hidden_spikes=hidden_total)

    # ---- recompensa ----------------------------------------------------------------------

    def reward(self, value: float) -> None:
        """Entrega dopamina `d = r − r̄` (erro de previsão: só surpresa ensina).

        Se as recompensas vêm sempre iguais (r̄ já as espera), `d` tende a zero e o aprendizado
        para; uma recompensa melhor que o esperado dá `d` > 0, pior dá `d` < 0.
        """
        dopamine = value - self._reward_baseline
        self._reward_baseline += self.config.baseline_rate * dopamine
        self._in_syn.apply_dopamine(dopamine)
        self._out_syn.apply_dopamine(dopamine)
        if value > 0:
            self._stats[0] += 1
        elif value < 0:
            self._stats[1] += 1

    # ---- salvar e restaurar --------------------------------------------------------------

    _FIXED_NAMES = ("w_hidden_hidden", "w_out_out")
    _PLASTIC = (
        ("w_in_hidden", "mask_in_hidden", "_in_syn"),
        ("w_hidden_out", "mask_hidden_out", "_out_syn"),
    )

    def state_dict(self) -> dict[str, np.ndarray]:
        """Pesos, máscaras, r̄ e estatísticas. Rastros e potenciais não: zeram ao abrir."""
        state = {name: getattr(self, name).copy() for name in self._FIXED_NAMES}
        for w_name, mask_name, attr in self._PLASTIC:
            syn: PlasticSynapses = getattr(self, attr)
            state[w_name] = syn.w.copy()
            state[mask_name] = syn.mask.copy()
        state["reward_baseline"] = np.array(self._reward_baseline)
        state["stats"] = self._stats.copy()
        return state

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        # Valida tudo ANTES de trocar qualquer peso: um estado ruim não deixa a rede pela metade.
        expected = {n: getattr(self, n).shape for n in self._FIXED_NAMES}
        for w_name, mask_name, attr in self._PLASTIC:
            shape = getattr(self, attr).w.shape
            expected[w_name] = expected[mask_name] = shape
        expected["reward_baseline"] = ()
        expected["stats"] = (3,)
        for name, shape in expected.items():
            if name not in state:
                raise ValueError(f"estado sem o campo {name!r}")
            if np.shape(state[name]) != shape:
                raise ValueError(
                    f"campo {name!r} com formato incompatível: {np.shape(state[name])}"
                )
        for name in self._FIXED_NAMES:
            setattr(self, name, np.array(state[name], dtype=float))
        for w_name, mask_name, attr in self._PLASTIC:
            old: PlasticSynapses = getattr(self, attr)
            new = PlasticSynapses(
                state[w_name], state[mask_name], old.w_max, old.cfg, old.normalize
            )
            setattr(self, attr, new)
        self._reward_baseline = float(state["reward_baseline"])
        self._stats = np.array(state["stats"], dtype=np.int64)
        # Voltar do disco é "acordar": potenciais e pulsos em trânsito começam do zero.
        self.hidden.reset()
        self.output.reset()
        self._hidden_spikes[:] = 0.0
        self._out_spikes[:] = 0.0
