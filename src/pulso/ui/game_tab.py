"""Aba "Jogo": jokenpô e par ou ímpar com o Pulso. Ganhou, fica contente; perdeu, fica bravo.

O rosto desta aba é um `PetWidget` próprio (a aba Pulso não está à vista enquanto se joga). O
resultado só mexe na **expressão** e no placar do dia, nunca na rede (ver `pulso.game`).
"""

import random

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pulso import game
from pulso.storage.db import GameStore
from pulso.ui import phrases
from pulso.ui.pet_widget import PetWidget

REACTION_S = 6.0  # o rosto de ganhou/perdeu dura mais que a reação ao carinho
_OUTCOME = {game.WON: phrases.GAME_WON, game.LOST: phrases.GAME_LOST, game.DRAW: phrases.GAME_DRAW}
_LOOK = {game.WON: "contente", game.LOST: "bravo"}
_BURST = {game.WON: "🎉", game.LOST: "💢", game.DRAW: "🤝"}


class GameTab(QWidget):
    def __init__(
        self,
        store: GameStore | None = None,
        rng: random.Random | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._rng = rng or random.Random()
        self.face = PetWidget(rng=random.Random())
        self.result = QLabel(phrases.GAME_INTRO)
        self.result.setObjectName("speech")
        self.result.setWordWrap(True)
        self.result.setMinimumHeight(self.result.fontMetrics().lineSpacing() * 3 + 28)
        self.score = QLabel()
        self.score.setObjectName("caption")
        self.picker = QComboBox()
        self.picker.addItems(["Jokenpô", "Par ou ímpar"])
        self.pages = QStackedWidget()
        self.picker.currentIndexChanged.connect(self.pages.setCurrentIndex)

        # Jokenpô: três botões de gesto.
        rps_page, rps_row = QWidget(), QHBoxLayout()
        self.rps_buttons: dict[str, QPushButton] = {}
        rps_row.addStretch()
        for move in game.RPS_MOVES:
            button = QPushButton(game.RPS_EMOJI[move])
            button.setToolTip(move.capitalize())
            button.setAccessibleName(move.capitalize())
            button.clicked.connect(lambda _=False, m=move: self.play_rps(m))
            self.rps_buttons[move] = button
            rps_row.addWidget(button)
        rps_row.addStretch()
        rps_page.setLayout(rps_row)
        self.pages.addWidget(rps_page)

        # Par ou ímpar: escolhe o lado, depois mostra de 0 a 5 dedos.
        eo_page, eo_col = QWidget(), QVBoxLayout()
        eo_col.setContentsMargins(0, 0, 0, 0)
        side_row = QHBoxLayout()
        self.side_buttons: dict[str, QPushButton] = {}
        self._sides = QButtonGroup(self)
        side_row.addStretch()
        for side in (game.EVEN, game.ODD):
            button = QPushButton(side.capitalize())
            button.setCheckable(True)
            self._sides.addButton(button)
            self.side_buttons[side] = button
            side_row.addWidget(button)
        side_row.addStretch()
        self.side_buttons[game.EVEN].setChecked(True)
        finger_row = QHBoxLayout()
        self.finger_buttons: list[QPushButton] = []
        finger_row.addStretch()
        for fingers in range(game.MAX_FINGERS + 1):
            button = QPushButton(str(fingers))
            button.setObjectName("mini")
            button.setToolTip(f"Mostrar {fingers} dedo(s)")
            button.clicked.connect(lambda _=False, f=fingers: self.play_even_odd(f))
            self.finger_buttons.append(button)
            finger_row.addWidget(button)
        finger_row.addStretch()
        eo_col.addLayout(side_row)
        eo_col.addLayout(finger_row)
        eo_page.setLayout(eo_col)
        self.pages.addWidget(eo_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self.face, stretch=3)
        layout.addWidget(self.result)
        layout.addWidget(self.picker)
        layout.addWidget(self.pages)
        layout.addWidget(self.score)
        self.refresh_score()

    # ---- jogadas -----------------------------------------------------------------------------

    def play_rps(self, move: str) -> game.Round:
        played = game.rps(move, self._rng)
        text = (
            f"Você {game.RPS_EMOJI[played.owner]} × Pulso {game.RPS_EMOJI[played.pet]}. "
            f"{_OUTCOME[played.result]}"
        )
        return self._finish(played, text)

    def play_even_odd(self, fingers: int) -> game.Round:
        side = game.EVEN if self.side_buttons[game.EVEN].isChecked() else game.ODD
        played = game.even_odd(side, fingers, self._rng)
        total = fingers + int(played.pet)
        parity = game.EVEN if total % 2 == 0 else game.ODD
        text = (
            f"Você ({side}) {fingers} + Pulso {played.pet} = {total}, deu {parity}. "
            f"{_OUTCOME[played.result]}"
        )
        return self._finish(played, text)

    def _finish(self, played: game.Round, text: str) -> game.Round:
        self.result.setText(text)
        look = _LOOK.get(played.result)
        if look:
            self.face.react(look, REACTION_S)
        self.face.burst(_BURST[played.result])
        if self._store is not None:
            self._store.record(played.game, played.result)
        self.refresh_score()
        return played

    def refresh_score(self) -> None:
        if self._store is None:
            self.score.setText("")
            return
        t = self._store.totals_today()
        self.score.setText(f"Hoje: Pulso {t['won']} × {t['lost']} você · {t['draw']} empate(s)")
