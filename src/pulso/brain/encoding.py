"""Codificação por taxa: transforma uma leitura dos sensores nas taxas de pulso da entrada.

Cada valor vira uma **taxa** (pulsos por segundo): quanto maior o valor, mais o neurônio "grita".
Dois jeitos de codificar:

- **Número (CPU, RAM, ociosidade, trocas de programa):** normalizado em [0, 1] e entregue a um par
  de grupos de neurônios, um "alto" (taxa = x · 100 Hz) e um "baixo" (taxa = (1 − x) · 100 Hz).
  Assim a rede reage tanto a "muita CPU" quanto a "pouca CPU" sem precisar de peso negativo.
- **Rótulo (categoria do programa, faixa do dia):** *one-hot*, um grupo de neurônios por valor
  possível. Só o grupo do valor atual dispara (100 Hz); os outros ficam em silêncio.

Cada "neurônio lógico" é repetido `REPEAT` vezes: a média de vários geradores de Poisson é bem menos
ruidosa que um só.

Uma leitura inválida (o sensor falhou) vira silêncio total: a rede não recebe informação inventada.
"""

import numpy as np

from pulso.sensors.base import SensorFrame

MAX_RATE_HZ = 100.0
REPEAT = 3  # geradores de Poisson por valor lógico

IDLE_SATURATION_S = 600.0  # 10 min sem mexer já conta como "ociosidade máxima"
SWITCHES_SATURATION = 10  # 10 trocas por minuto já é "agitação máxima"
HOUR_BAND_H = 4  # faixas do dia de 4 h → 6 faixas

CATEGORIES = ("codigo", "navegador", "video", "chat", "escritorio", "jogo", "outro")
N_HOUR_BANDS = 24 // HOUR_BAND_H
N_SCALARS = 4  # cpu, ram, ociosidade, trocas
N_INPUTS = (N_SCALARS * 2 + len(CATEGORIES) + N_HOUR_BANDS) * REPEAT


def _clip01(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def encode(frame: SensorFrame) -> np.ndarray:
    """Devolve o vetor de taxas (Hz) com `N_INPUTS` posições."""
    if not frame.valid:
        return np.zeros(N_INPUTS)

    scalars = (
        frame.cpu_percent / 100.0,
        frame.ram_percent / 100.0,
        frame.idle_seconds / IDLE_SATURATION_S,
        frame.app_switches_last_min / SWITCHES_SATURATION,
    )
    logical = []
    for x in map(_clip01, scalars):
        logical += [x, 1.0 - x]  # grupo "alto" e grupo "baixo"

    category = frame.category if frame.category in CATEGORIES else "outro"
    logical += [1.0 if c == category else 0.0 for c in CATEGORIES]

    band = int(frame.hour_of_day % 24) // HOUR_BAND_H
    logical += [1.0 if b == band else 0.0 for b in range(N_HOUR_BANDS)]

    return np.repeat(np.array(logical), REPEAT) * MAX_RATE_HZ
