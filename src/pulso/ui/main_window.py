"""Janela principal: abas (por enquanto só "Pet") e o laço de 1 s no `QTimer`.

Conceitos de Qt usados aqui:
- **Sinal e *slot***: um botão emite o sinal `clicked`; ligamos (`connect`) esse sinal a um método
  nosso (o *slot*), que o Qt chama quando o clique acontece.
- **`QTimer`**: dispara o sinal `timeout` a cada intervalo, dentro do laço de eventos do Qt, sem
  threads. A leitura do sensor e a rede custam poucos ms, então cabem na thread da interface.
"""

import random

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pulso.clock import Clock
from pulso.controller import PetController
from pulso.ui import phrases
from pulso.ui.pet_widget import PetWidget

WELCOME_HOLD_S = 30.0  # a fala de boas-vindas não é trocada por humores antes disto
ICON_PX = 20


def pause_icon(paused: bool, color: QColor) -> QIcon:
    """Ícone desenhado na cor do texto: duas barras (pausar) ou um triângulo (retomar)."""
    pixmap = QPixmap(
        ICON_PX * 2, ICON_PX * 2
    )  # o dobro de pixels: nítido em telas de alta densidade
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    s = ICON_PX * 2
    if paused:  # ▶
        tri = QPainterPath()
        tri.moveTo(s * 0.28, s * 0.15)
        tri.lineTo(s * 0.28, s * 0.85)
        tri.lineTo(s * 0.85, s * 0.5)
        tri.closeSubpath()
        p.drawPath(tri)
    else:  # ⏸
        p.drawRoundedRect(QRectF(s * 0.22, s * 0.16, s * 0.2, s * 0.68), 3, 3)
        p.drawRoundedRect(QRectF(s * 0.58, s * 0.16, s * 0.2, s * 0.68), 3, 3)
    p.end()
    return QIcon(pixmap)


def _lines_height(label: QLabel, lines: int) -> int:
    """Altura para `lines` linhas de texto do `label` (mais a margem interna do estilo)."""
    return label.fontMetrics().lineSpacing() * lines + 28


class PetTab(QWidget):
    """T01 do Design Brief: selo, rosto, balão de fala e os botões."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.badge = QLabel()
        self.badge.setObjectName("badge")
        self.pet = PetWidget()
        self.speech = QLabel()
        self.speech.setObjectName("speech")
        self.speech.setWordWrap(True)
        self.speech.setMinimumHeight(_lines_height(self.speech, 3))  # o rosto nunca é coberto
        self.caption = QLabel()
        self.caption.setObjectName("caption")
        self.caption.setWordWrap(True)
        self.caption.setMinimumHeight(_lines_height(self.caption, 2))
        self.caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.care = QPushButton("💚 Carinho")
        self.care.setObjectName("care")
        self.scold = QPushButton("💢 Bronca")
        self.pause = QPushButton()
        self.pause.setObjectName("pause")
        self.pause.setIconSize(QSize(ICON_PX, ICON_PX))
        self.pause.setFixedHeight(self.care.sizeHint().height())  # mesma altura dos vizinhos

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        row.addWidget(self.care)
        row.addWidget(self.scold)
        row.addWidget(self.pause)  # ao lado dos demais, só o ícone
        row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignHCenter)  # só se pausado
        layout.addWidget(self.caption)  # o que o humor significa, acima do rosto
        layout.addWidget(self.pet, stretch=11)
        layout.addWidget(self.speech, stretch=2)
        layout.addLayout(row)
        self.show_paused(False)

    def show_paused(self, paused: bool) -> None:
        # Sem aviso constante: o selo só aparece quando há algo a dizer (observação pausada).
        self.badge.setText("😴 Observação pausada")
        self.badge.setVisible(paused)
        self.badge.setProperty("paused", paused)
        self.badge.style().unpolish(self.badge)  # faz o Qt reler o estilo da propriedade
        self.badge.style().polish(self.badge)
        label = "Retomar observação" if paused else "Pausar observação"
        self.pause.setIcon(pause_icon(paused, self.palette().windowText().color()))
        self.pause.setToolTip(
            "Volta a observar o computador." if paused
            else "Pausa a observação (privacidade): o Pulso para de ler o computador."
        )  # fmt: skip
        self.pause.setAccessibleName(label)
        self.care.setEnabled(not paused)
        self.scold.setEnabled(not paused)


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: PetController,
        clock: Clock,
        first_run: bool = False,
        tick_ms: int = 1000,
        rng: random.Random | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Pulso")
        self._controller = controller
        self._clock = clock
        self._rng = rng or random.Random()
        self._hold_until = clock.now() + WELCOME_HOLD_S if first_run else 0.0

        self.pet_tab = PetTab()
        tabs = QTabWidget()
        tabs.addTab(self.pet_tab, "Pet")  # "Cérebro" e "Saúde" entram nas etapas 5 e 6
        self.setCentralWidget(tabs)

        self.pet_tab.care.clicked.connect(lambda: self._owner_click(+1))
        self.pet_tab.scold.clicked.connect(lambda: self._owner_click(-1))
        self.pet_tab.pause.clicked.connect(self.toggle_pause)

        self._say(phrases.WELCOME if first_run else phrases.GREETING, force=True)
        self._show_mood(controller.mood)
        self._fit_to_minimum()

        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self.tick)
        self._timer.start()

    def _fit_to_minimum(self) -> None:
        """Abre sempre no menor tamanho possível (e não deixa encolher além dele).

        O Qt não conta as quebras de linha dos textos no tamanho mínimo, então a altura sai de
        `totalHeightForWidth`, que pergunta ao layout quanto precisa numa largura dada.
        """
        tabs = self.centralWidget()
        width = self.minimumSizeHint().width()
        height = (
            self.pet_tab.layout().totalHeightForWidth(width) + tabs.tabBar().sizeHint().height()
        )
        self.setMinimumSize(width, height)
        self.resize(width, height)

    # ---- laço de 1 s -------------------------------------------------------------------------

    def tick(self) -> None:
        """Uma volta do laço (o `QTimer` chama; os testes também)."""
        result = self._controller.tick()
        if result is None:  # pausado: o controlador não leu nada
            return
        self._show_mood(result.mood)
        if result.mood_changed and result.mood is not None:
            self._say(phrases.mood_phrase(result.mood, self._rng))

    # ---- botões ------------------------------------------------------------------------------

    def _owner_click(self, sign: int) -> None:
        pet = self.pet_tab.pet
        pet.burst("💚" if sign > 0 else "💢")  # retorno visual imediato
        pet.react("contente" if sign > 0 else "arrependido")  # depois, volta ao humor
        self._controller.owner_reward(sign)
        self._say(phrases.PETTED if sign > 0 else phrases.SCOLDED, force=True)

    def toggle_pause(self) -> None:
        if self._controller.paused:
            self._controller.resume()
            self._show_mood(self._controller.mood)
            self._say(phrases.RESUMED, force=True)
        else:
            self._controller.pause()
            self._show_mood(phrases.SLEEPING)
            self._say(phrases.PAUSED, force=True)
        self.pet_tab.show_paused(self._controller.paused)

    def _show_mood(self, mood: str | None) -> None:
        """Põe o humor no rosto e escreve embaixo o que ele significa."""
        self.pet_tab.pet.set_mood(mood)
        if mood == phrases.SLEEPING:
            meaning = phrases.MEANING_SLEEPING
        else:
            meaning = phrases.MOOD_MEANINGS.get(mood, phrases.MEANING_NEW)
        self.pet_tab.caption.setText(meaning)
        self.pet_tab.pet.setToolTip(f"{meaning}\n{phrases.MEANING_HINT}")

    # ---- fala --------------------------------------------------------------------------------

    def _say(self, text: str, force: bool = False) -> None:
        """Mostra uma fala. Sem `force`, respeita a retenção da fala de boas-vindas."""
        if not force and self._clock.now() < self._hold_until:
            return
        if force:
            self._hold_until = 0.0
        self.pet_tab.speech.setText(text)

    # ---- fechar ------------------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (nome do Qt)
        self._timer.stop()
        self._controller.shutdown()  # guarda o cérebro
        super().closeEvent(event)
