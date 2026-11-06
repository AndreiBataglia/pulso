"""O contrato trocável do cérebro (`Engine`).

Qualquer motor que aprende *online* (enquanto roda) pode ser plugado aqui sem mexer no resto: o
codificador, o decodificador e as regras de recompensa ficam fora do motor (TRD §5.2).

O contrato cresce com as etapas, sempre acompanhado pelo teste de contrato:
- etapa 2: `step`, `state_dict`, `load_state_dict`;
- etapa 3: `reward` (dopamina);
- etapa 5: `snapshot` (dados para os gráficos) e `reward` passa a devolver a dopamina.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class StepResult:
    """O que o motor devolve depois de simular um trecho de tempo."""

    counts: np.ndarray  # pulsos de cada grupo de saída (um humor por grupo), na ordem de `groups`
    hidden_spikes: int  # pulsos da camada oculta no trecho (mede a atividade da rede)


@dataclass(frozen=True)
class BrainSnapshot:
    """Uma fotografia da rede para os gráficos da aba Cérebro (cópias: pode ser guardada à vontade).

    Os pulsos e os potenciais estão em **tempo de rede** (1 coluna = 1 ms simulado), do mais
    antigo para o mais novo. Como a rede simula 100 ms a cada 1 s real, o trecho mostrado é de
    vários segundos reais costurados (TRD §5.1, "dois relógios").
    """

    spikes: np.ndarray  # bool [neurônio, ms]: entrada, depois oculta, depois saída
    layers: list[tuple[str, int, int]]  # (tipo, primeira linha, última+1) em `spikes`
    groups: list[str]  # humores, na ordem dos grupos de saída
    group_size: int  # neurônios de saída por humor
    voltage: np.ndarray  # [traço, ms], em mV
    voltage_labels: list[str]
    v_rest_mv: float
    v_threshold_mv: float
    weights: np.ndarray  # oculta excitatória → saída, [pré, pós]
    weights_max: float
    dopamine: float  # a última dopamina entregue (d = r − r̄)
    reward_baseline: float  # r̄
    rewards: tuple[int, int]  # recompensas positivas e negativas desde o começo


class Engine(Protocol):
    n_inputs: int  # tamanho do vetor de taxas que `step` espera
    groups: list[str]  # nomes dos grupos de saída (os humores)

    def step(self, rates_hz: np.ndarray, duration_ms: int) -> StepResult:
        """Simula `duration_ms` de tempo da rede com as taxas de entrada (em Hz) constantes."""
        ...

    def reward(self, value: float) -> float:
        """Dopamina: `value` > 0 reforça o que a rede fez há pouco, `value` < 0 desfaz.

        Devolve a dopamina entregue (`value − r̄`), para quem quiser desenhá-la.
        """
        ...

    def snapshot(self) -> BrainSnapshot:
        """Dados para os gráficos: pulsos e potenciais recentes, dopamina e pesos."""
        ...

    def state_dict(self) -> dict[str, np.ndarray]:
        """Tudo que precisa ser salvo para reconstruir o cérebro."""
        ...

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        """Restaura o que `state_dict` devolveu. Formato incompatível → `ValueError`."""
        ...
