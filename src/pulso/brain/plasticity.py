"""Sinapses plásticas: STDP com rastro de elegibilidade e dopamina (R-STDP, regra de três fatores).

Os três fatores são: atividade do **pré** (neurônio que manda), atividade do **pós**
(que recebe) e a **dopamina** (recompensa). A ideia, em três passos:

1. **STDP** (*spike-timing-dependent plasticity*): se o pré dispara um pouco *antes* do pós, ele
   provavelmente ajudou a causar o disparo → a sinapse "merece" ficar mais forte (LTP). Se o pré
   dispara *depois* do pós, não causou nada → "merece" ficar mais fraca (LTD). Para medir "um pouco
   antes", cada neurônio deixa um **rastro** que sobe a 1 quando ele dispara e decai com τ = 20 ms.
2. **Elegibilidade:** o resultado do STDP *não* muda o peso na hora. Vai para um segundo rastro, a
   elegibilidade `e`, que decai devagar (τe). É uma "etiqueta" que diz: *esta sinapse participou há
   pouco*. Isso resolve o problema da **recompensa atrasada**: o carinho chega segundos depois do
   comportamento, e a etiqueta ainda está lá.
3. **Dopamina:** só quando chega `d` o peso muda: `Δw = η · d · e`. Sem dopamina, nada
   muda. Com `d` > 0
   as etiquetas positivas viram reforço; com `d` < 0 viram punição.

**Dois relógios (TRD §5.1):** a rede simula 100 ms a cada 1 s real, 10× mais devagar.
Por isso o `τe` é
dado em **tempo de rede** (`tau_e_net_ms`): 1000 ms de rede ≈ 10 s reais.

**Estabilidade:** os pesos ficam em [0, w_max] e cada neurônio pós mantém a soma dos
pesos que recebe
(*normalização sináptica*). Assim, reforçar umas sinapses enfraquece as outras, e a rede não satura.
"""

from dataclasses import dataclass

import numpy as np

from pulso.brain.lif import DT_MS


@dataclass(frozen=True)
class PlasticityConfig:
    tau_trace_ms: float = 20.0  # rastros pré e pós do STDP
    a_plus: float = 1.0  # intensidade do LTP (pré antes de pós)
    a_minus: float = 1.05  # intensidade do LTD, um pouco maior: evita que tudo só suba
    tau_e_net_ms: float = 1000.0  # elegibilidade, em tempo de REDE (≈ 10 s reais)
    eta: float = (
        0.003  # taxa de aprendizado: fração de w_max por unidade de (dopamina × elegibilidade)
    )
    elig_floor: float = 0.05  # piso do RMS: com a rede quase muda, a recompensa quase não age
    max_step_fraction: float = 0.5  # um único pulso de dopamina muda no máximo isto de w_max


class PlasticSynapses:
    """Pesos `w[pré, pós]` que aprendem. Só as conexões da `mask` existem e podem mudar."""

    def __init__(
        self,
        weights: np.ndarray,
        mask: np.ndarray,
        w_max: float,
        config: PlasticityConfig | None = None,
        normalize: str = "post",
    ) -> None:
        if normalize not in ("post", "pre"):
            raise ValueError(f"normalize deve ser 'post' ou 'pre', recebi {normalize!r}")
        # "post": cada neurônio que recebe mantém a soma dos pesos de entrada.
        # "pre": cada neurônio que manda mantém a soma dos pesos de saída (distribui uma
        # influência fixa entre os destinos: reforçar um destino tira dos outros).
        self.normalize = normalize
        self._axis = 0 if normalize == "post" else 1
        self.cfg = config or PlasticityConfig()
        self.w_max = w_max
        self.mask = np.asarray(mask, dtype=bool)
        self.w = np.where(self.mask, weights, 0.0).astype(float)
        # A soma que a normalização mantém constante (a do sorteio inicial).
        self.target_sum = self.w.sum(axis=self._axis, keepdims=True)
        self._trace_decay = np.exp(-DT_MS / self.cfg.tau_trace_ms)
        self._elig_decay = np.exp(-DT_MS / self.cfg.tau_e_net_ms)
        self.pre_trace = np.zeros(self.w.shape[0])
        self.post_trace = np.zeros(self.w.shape[1])
        self.eligibility = np.zeros_like(self.w)

    def reset_traces(self) -> None:
        """Zera rastros e elegibilidade (o "acordar" depois de carregar do disco)."""
        self.pre_trace[:] = 0.0
        self.post_trace[:] = 0.0
        self.eligibility[:] = 0.0

    def update(self, pre_spikes: np.ndarray, post_spikes: np.ndarray) -> None:
        """Um passo de 1 ms: atualiza rastros e acumula o STDP na elegibilidade (peso NÃO muda)."""
        c = self.cfg
        self.pre_trace = self.pre_trace * self._trace_decay + pre_spikes
        # LTP: pós dispara agora, o pré disparou há pouco (o rastro do pré inclui o passo atual:
        # o pulso que chegou neste passo ajudou a causar este disparo).
        # LTD: pré chega agora, o pós disparou há pouco (o rastro do pós ainda não tem este passo).
        self.eligibility *= self._elig_decay
        # Os pulsos são raros: só vale pagar o produto externo quando alguém disparou.
        if post_spikes.any():
            self.eligibility += c.a_plus * np.outer(self.pre_trace, post_spikes) * self.mask
        if pre_spikes.any():
            self.eligibility -= c.a_minus * np.outer(pre_spikes, self.post_trace) * self.mask
        self.post_trace = self.post_trace * self._trace_decay + post_spikes

    def apply_dopamine(self, dopamine: float) -> None:
        """Chegou a dopamina: `Δw = η · d · e`, com limites e normalização por neurônio."""
        c = self.cfg
        # Elegibilidade normalizada: cada recompensa move um "orçamento" de peso parecido, em vez
        # de deixar o contexto mais barulhento (mais pulsos) levar todo o reforço.
        rms = float(np.sqrt(np.sum(self.eligibility**2) / max(self.mask.sum(), 1)))
        scale = max(rms, c.elig_floor)
        delta = c.eta * dopamine * (self.eligibility / scale) * self.w_max
        limit = c.max_step_fraction * self.w_max
        self.w = np.clip(self.w + np.clip(delta, -limit, limit), 0.0, self.w_max) * self.mask
        self._normalize()

    def _normalize(self) -> None:
        """Devolve a cada neurônio a soma de pesos original (reforçar uns enfraquece outros)."""
        current = self.w.sum(axis=self._axis, keepdims=True)
        scale = np.divide(self.target_sum, current, out=np.ones_like(current), where=current > 0)
        self.w = np.clip(self.w * scale, 0.0, self.w_max)
