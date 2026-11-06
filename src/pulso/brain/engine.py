"""O contrato trocável do cérebro (`Engine`).

Qualquer motor que aprende *online* (enquanto roda) pode ser plugado aqui sem mexer no resto: o
codificador, o decodificador e as regras de recompensa ficam fora do motor (TRD §5.2).

O contrato cresce com as etapas, sempre acompanhado pelo teste de contrato:
- etapa 2: `step`, `state_dict`, `load_state_dict`;
- etapa 3: `reward` (dopamina);
- etapa 5: `snapshot` (dados para os gráficos).
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class StepResult:
    """O que o motor devolve depois de simular um trecho de tempo."""

    counts: np.ndarray  # pulsos de cada grupo de saída (um humor por grupo), na ordem de `groups`
    hidden_spikes: int  # pulsos da camada oculta no trecho (mede a atividade da rede)


class Engine(Protocol):
    n_inputs: int  # tamanho do vetor de taxas que `step` espera
    groups: list[str]  # nomes dos grupos de saída (os humores)

    def step(self, rates_hz: np.ndarray, duration_ms: int) -> StepResult:
        """Simula `duration_ms` de tempo da rede com as taxas de entrada (em Hz) constantes."""
        ...

    def reward(self, value: float) -> None:
        """Dopamina: `value` > 0 reforça o que a rede fez há pouco, `value` < 0 desfaz."""
        ...

    def state_dict(self) -> dict[str, np.ndarray]:
        """Tudo que precisa ser salvo para reconstruir o cérebro."""
        ...

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        """Restaura o que `state_dict` devolveu. Formato incompatível → `ValueError`."""
        ...
