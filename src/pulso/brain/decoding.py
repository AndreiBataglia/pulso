"""Decodificação: contagem de pulsos por grupo de saída → humor, com histerese.

A rede dispara o tempo todo; o humor é decidido só a cada 10 s (10 voltas do laço), somando os
pulsos de cada grupo nesse intervalo. O grupo que mais pulsou vence.

**Histerese:** para trocar o humor atual, o desafiante precisa vencer com folga (`margin`). Sem
isso, dois grupos quase empatados fariam o Pulso trocar de cara a cada decisão. A palavra vem de
"ficar para trás": o estado atual tem uma vantagem, como o termostato que só liga 1 grau acima do
ponto em que desliga.
"""

import numpy as np

WINDOW_STEPS = 10  # voltas do laço (1 s cada) por decisão → 10 s


class MoodDecoder:
    def __init__(
        self,
        moods: list[str],
        window_steps: int = WINDOW_STEPS,
        margin: float = 0.25,
        initial: str | None = None,
    ) -> None:
        if initial is not None and initial not in moods:
            raise ValueError(f"humor inicial desconhecido: {initial!r}")
        self.moods = list(moods)
        self.mood: str | None = initial  # humor atual (None até a primeira decisão com pulsos)
        self._window_steps = window_steps
        self._margin = margin
        self._acc = np.zeros(len(moods))
        self._steps = 0
        self._last_window = np.zeros(len(moods))  # contagem da última janela de 10 s fechada

    def counts(self) -> np.ndarray:
        """Pulsos por humor para os gráficos: a última janela fechada (ou, antes da primeira
        decisão, o que já se juntou nesta)."""
        if self._last_window.any():
            return self._last_window.copy()
        return self._acc.copy()

    def update(self, counts: np.ndarray) -> str | None:
        """Soma a contagem de uma volta. Ao fechar a janela, devolve o humor; senão, `None`."""
        self._acc += counts
        self._steps += 1
        if self._steps < self._window_steps:
            return None
        window, self._acc, self._steps = self._acc, np.zeros(len(self.moods)), 0
        self._last_window = window
        return self._decide(window)

    def _decide(self, window: np.ndarray) -> str | None:
        best = int(np.argmax(window))
        if window[best] == 0:  # rede muda: sem informação, mantém o humor atual
            return self.mood
        challenger = self.moods[best]
        if self.mood is None:
            self.mood = challenger
        elif challenger != self.mood:
            current = window[self.moods.index(self.mood)]
            if window[best] > current * (1.0 + self._margin):
                self.mood = challenger
        return self.mood
