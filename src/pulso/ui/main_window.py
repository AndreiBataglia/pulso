"""Janela principal: abas "Pulso", "Jogo" e "Cérebro" e o laço de 1 s no `QTimer`.

A aba Pulso é a direção D do canvas de design (`docs/design/canvas/`): rosto redondo com o anel do
foco, pílula do modo, balão de fala e **um painel por fase do ciclo** (cronômetro, lembrete,
"o que foi?", descanso). Durante o lembrete e a pergunta da volta, a grade de ações some e só
ficam as respostas.

Conceitos de Qt usados aqui:
- **Sinal e *slot***: um botão emite o sinal `clicked`; ligamos (`connect`) esse sinal a um método
  nosso (o *slot*), que o Qt chama quando o clique acontece.
- **`QTimer`**: dispara o sinal `timeout` a cada intervalo, dentro do laço de eventos do Qt, sem
  threads. A leitura do sensor e a rede custam poucos ms, então cabem na thread da interface.
"""

import math
import random
from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pulso.clock import Clock
from pulso.controller import PetController
from pulso.habits import kinds
from pulso.habits.focus_cycle import Mode, Phase
from pulso.storage.autostart import Autostart
from pulso.storage.config import Settings, habit_config
from pulso.storage.db import GameStore
from pulso.ui import phrases
from pulso.ui.brain_tab import BRAIN_MINIMUM, BRAIN_PREFERRED, BrainTab
from pulso.ui.game_tab import GameTab
from pulso.ui.pet_widget import PetWidget
from pulso.ui.settings_dialog import SettingsDialog
from pulso.ui.theme import LIGHT, Palette, phase_colors
from pulso.ui.tray import Tray

WELCOME_HOLD_S = 30.0  # a fala de boas-vindas não é trocada por humores antes disto
ICON_PX = 20
PET_WIDTH = 360  # largura mínima da aba Pulso: comporta o painel mais largo ("o que foi?")


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


def _mmss(seconds: float) -> str:
    total = max(int(seconds), 0)
    return f"{total // 60:02d}:{total % 60:02d}"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _set_property(widget: QWidget, name: str, value: bool) -> None:
    """Muda uma propriedade usada pelo estilo e faz o Qt reler o estilo do widget."""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)  # sem isto o Qt não reaplica o seletor `[name="true"]`
    widget.style().polish(widget)


def _card(alert: bool = False) -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    card.setProperty("alert", alert)
    card.setProperty("dim", False)
    return card


def _label(object_name: str, wrap: bool = False, center: bool = False) -> QLabel:
    label = QLabel()
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    if center:
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    return label


class PetTab(QWidget):
    """T01 do Design Brief, na direção D: rosto com anel, balão e um painel por fase do ciclo."""

    def __init__(self, palette: Palette = LIGHT, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_color = QColor(palette.text)  # o texto do tema, não o do sistema (modo escuro)
        self.badge = QLabel()
        self.badge.setObjectName("badge")
        self.state_label = _label("state")
        self.mode_button = QPushButton()
        self.mode_button.setObjectName("pill")
        self.pause = QPushButton()
        self.pause.setObjectName("pause")
        self.pause.setIconSize(QSize(ICON_PX, ICON_PX))
        self.pause.setFixedHeight(34)
        self.pet = PetWidget()
        self.speech = QLabel()
        self.speech.setObjectName("speech")
        self.speech.setWordWrap(True)
        self.speech.setMinimumHeight(_lines_height(self.speech, 3))  # o rosto nunca é coberto
        self.caption = _label("caption", wrap=True, center=True)
        self.caption.setMinimumHeight(_lines_height(self.caption, 2))

        # Cartão do cronômetro (foco, aguardando, reunião, casual).
        self.timer_card = _card()
        self.timer_caption = _label("caption")
        self.timer_value = _label("bigtime")
        self.take_break = QPushButton("Pausar agora")
        self.take_break.setObjectName("primary")
        self.skip = QPushButton("⏭")
        self.skip.setObjectName("round")
        self.skip.setAccessibleName("Pular fase")

        # Lembrete de pausa: só as respostas.
        self.reminder_card = _card(alert=True)
        self.reminder_title = _label("cardtitle", wrap=True, center=True)
        self.reminder_hint = _label("caption", wrap=True, center=True)
        self.pause_now = QPushButton("Pausar agora")
        self.pause_now.setObjectName("primary")
        self.postpone = QPushButton("Prorrogar 5 min")
        self.postpone.setObjectName("ghost")
        self.decline_break = QPushButton("Hoje não")
        self.decline_break.setObjectName("link")

        # "O que foi?": as quatro respostas da volta.
        self.away_card = _card()
        self.away_title = _label("cardtitle", wrap=True, center=True)
        self.away_hint = _label("caption", wrap=True, center=True)
        self.away_buttons: dict[str, QPushButton] = {}
        for key, text in (
            (kinds.CAT_PAUSE, "Pausa"),
            (kinds.CAT_MEAL, "Refeição"),
            (kinds.CAT_NEED, "Necessidade"),
            (kinds.CAT_FOCUS, "Foco sem mexer"),
        ):
            button = QPushButton(text)
            button.setObjectName("primary" if key == kinds.CAT_PAUSE else "ghost")
            self.away_buttons[key] = button

        # Descanso (e o que passa dele).
        self.rest_card = _card()
        self.rest_label = _label("caption", wrap=True, center=True)
        self.end_break = QPushButton("Voltar ao foco antes")
        self.end_break.setObjectName("ghost")

        # Grade de ações (some no lembrete e na pergunta da volta) e a linha da água.
        self.care = QPushButton("💚 Carinho")
        self.drink = QPushButton("💧 Bebi")
        for button in (self.care, self.drink):
            button.setObjectName("action")
        self.later = QPushButton("Depois")
        self.decline = QPushButton("Hoje não")
        for mini in (self.later, self.decline):
            mini.setObjectName("mini")  # botões secundários: menores que Carinho/Bebi
        self.footer_left = _label("caption")
        self.footer_right = _label("caption")
        self.footer_right.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._set_tooltips()
        self._build_layout()
        self.show_panel("timer")
        self.show_asking(False)
        self.show_mode(Mode.PROFESSIONAL)
        self.show_paused(False)

    def _set_tooltips(self) -> None:
        tips = {
            self.care: "Um carinho: o Pulso aprende que você gostou do jeito dele.",
            self.drink: "Bebi água: zera o lembrete de água.",
            self.later: "Depois: me lembra de novo em alguns minutos.",
            self.decline: "Hoje não: deixa passar (conta como recusa).",
            self.take_break: "Pausar agora: adianta o descanso.",
            self.pause_now: "Pausar agora: começa o descanso.",
            self.skip: "Pula a fase atual.",
            self.postpone: "Prorrogar: volto a chamar em 5 minutos (fica anotado).",
            self.decline_break: "Hoje não: sigo sem descansar (conta como recusa).",
            self.end_break: "Volta ao foco antes do fim; a pausa feita pela metade também conta.",
            self.away_buttons[kinds.CAT_PAUSE]: "Pausa: conta como descanso, mesmo parcial.",
            self.away_buttons[kinds.CAT_MEAL]: "Refeição: descanso longo, sem cobrança.",
            self.away_buttons[kinds.CAT_NEED]: (
                "Necessidade (banheiro, algo rápido): não conta como pausa nem penaliza."
            ),
            self.away_buttons[kinds.CAT_FOCUS]: (
                "Foco sem mexer (leitura, vídeo): o tempo fora vira foco."
            ),
        }
        for button, tip in tips.items():
            button.setToolTip(tip)

    def _build_layout(self) -> None:
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self.state_label)
        top.addStretch()
        top.addWidget(self.mode_button)
        top.addWidget(self.pause)

        timer = QHBoxLayout(self.timer_card)
        timer.setContentsMargins(18, 10, 12, 10)
        timer.setSpacing(10)
        numbers = QVBoxLayout()
        numbers.setSpacing(0)
        numbers.addWidget(self.timer_caption)
        numbers.addWidget(self.timer_value)
        timer.addLayout(numbers, stretch=1)
        timer.addWidget(self.take_break)
        timer.addWidget(self.skip)

        reminder = QVBoxLayout(self.reminder_card)
        reminder.setContentsMargins(14, 12, 14, 10)
        reminder.setSpacing(8)
        for widget in (
            self.reminder_title, self.reminder_hint, self.pause_now, self.postpone,
        ):  # fmt: skip
            reminder.addWidget(widget)
        reminder.addWidget(self.decline_break, alignment=Qt.AlignmentFlag.AlignHCenter)

        away = QVBoxLayout(self.away_card)
        away.setContentsMargins(14, 12, 14, 10)
        away.setSpacing(8)
        away.addWidget(self.away_title)
        answers = QGridLayout()
        answers.setSpacing(8)
        for index, button in enumerate(self.away_buttons.values()):
            answers.addWidget(button, index // 2, index % 2)
        away.addLayout(answers)
        away.addWidget(self.away_hint)

        rest = QVBoxLayout(self.rest_card)
        rest.setContentsMargins(14, 10, 14, 10)
        rest.setSpacing(8)
        rest.addWidget(self.rest_label)
        rest.addWidget(self.end_break)

        self.grid = QWidget()
        grid = QHBoxLayout(self.grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        grid.addWidget(self.care, stretch=1)
        grid.addWidget(self.drink, stretch=1)

        # Linha própria (só durante um lembrete de água): a janela cresce uma linha e depois volta.
        self.ask_row = QWidget()
        asking = QHBoxLayout(self.ask_row)
        asking.setContentsMargins(0, 0, 0, 0)
        asking.setSpacing(8)
        asking.addStretch()
        asking.addWidget(self.later)
        asking.addWidget(self.decline)
        asking.addStretch()

        footer = QHBoxLayout()
        footer.addWidget(self.footer_left)
        footer.addStretch()
        footer.addWidget(self.footer_right)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(8)
        layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignHCenter)  # só se pausado
        layout.addLayout(top)
        layout.addWidget(self.caption)  # o que o humor significa, acima do rosto
        layout.addWidget(self.pet, stretch=11)
        layout.addWidget(self.speech, stretch=2)
        for card in self.panels.values():
            layout.addWidget(card)
        layout.addWidget(self.grid)
        layout.addWidget(self.ask_row)
        layout.addLayout(footer)

    @property
    def panels(self) -> dict[str, QFrame]:
        return {
            "timer": self.timer_card,
            "reminder": self.reminder_card,
            "away": self.away_card,
            "rest": self.rest_card,
        }

    # ---- o que a janela mostra ----------------------------------------------------------------

    def show_panel(self, name: str) -> None:
        """Um painel por vez; no lembrete e na pergunta da volta, a grade e o balão somem."""
        for key, card in self.panels.items():
            card.setVisible(key == name)
        asking = name in ("reminder", "away")  # o próprio painel é o balão: só as respostas
        self.grid.setVisible(not asking)
        self.speech.setVisible(not asking)

    @property
    def panel(self) -> str:
        return next(key for key, card in self.panels.items() if not card.isHidden())

    def show_asking(self, water: bool) -> None:
        """Os botões "Depois" e "Hoje não" da água só existem com o lembrete esperando resposta."""
        self.ask_row.setVisible(water)

    def set_state(self, text: str, color: str) -> None:
        self.state_label.setText(text)
        self.state_label.setStyleSheet(f"color: {color};")

    def show_timer(self, caption: str, value: str, *, dim: bool, buttons: bool) -> None:
        """O cartão do cronômetro. Os botões só existem com o foco rodando."""
        self.timer_caption.setText(caption)
        self.timer_value.setText(value)
        _set_property(self.timer_card, "dim", dim)
        self.take_break.setVisible(buttons)
        self.skip.setVisible(buttons)

    def show_mode(self, mode: Mode) -> None:
        casual = mode is Mode.CASUAL
        self.mode_button.setText("Casual" if casual else "Profissional")
        self.mode_button.setToolTip(
            "Modo casual: só lembro da água. Clique para voltar ao profissional."
            if casual
            else "Modo profissional: conto o foco e chamo para a pausa. Clique para o casual."
        )
        self.mode_button.setAccessibleName(f"Modo {mode.value}")
        _set_property(self.mode_button, "casual", casual)

    def show_paused(self, paused: bool) -> None:
        # Sem aviso constante: o selo só aparece quando há algo a dizer (observação pausada).
        self.badge.setText("😴 Observação pausada")
        self.badge.setVisible(paused)
        self.badge.setProperty("paused", paused)
        self.badge.style().unpolish(self.badge)  # faz o Qt reler o estilo da propriedade
        self.badge.style().polish(self.badge)
        label = "Retomar observação" if paused else "Pausar observação"
        self.pause.setIcon(pause_icon(paused, self._icon_color))
        self.pause.setToolTip(
            "Volta a observar o computador." if paused
            else "Pausa a observação (privacidade): o Pulso para de ler o computador."
        )  # fmt: skip
        self.pause.setAccessibleName(label)
        self.care.setEnabled(not paused)


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: PetController,
        clock: Clock,
        first_run: bool = False,
        tick_ms: int = 1000,
        rng: random.Random | None = None,
        palette: Palette = LIGHT,
        tray: Tray | None = None,
        settings: Settings | None = None,
        save_settings: Callable[[Settings], None] = lambda settings: None,
        autostart: Autostart | None = None,
        scores: GameStore | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Pulso")
        self._controller = controller
        self._tray = tray  # bandeja e avisos do Windows (None = sem eles)
        self._settings = settings or Settings()
        self._save_settings = save_settings
        self._autostart = autostart  # None = sem a opção "Iniciar com o Windows"
        self._quitting = False  # "Sair" de verdade (o X só esconde, se houver bandeja)
        self._told_tray = False  # já avisou, nesta sessão, que ficou na bandeja?
        self._was_nervous = False
        self._layout_key: tuple[str, bool] = ("timer", False)  # painel e água na janela
        self._phase = controller.habits.cycle.phase  # para narrar só as viradas de fase
        self._colors = phase_colors(palette)
        self._clock = clock
        self._rng = rng or random.Random()
        self._hold_until = clock.now() + WELCOME_HOLD_S if first_run else 0.0

        self.pet_tab = PetTab(palette)
        self.game_tab = GameTab(scores, rng)
        self.brain_tab = BrainTab(controller, clock, palette)
        self.tabs = tabs = QTabWidget()
        tabs.addTab(self.pet_tab, "Pulso")  # "Saúde" entra na etapa 8
        tabs.addTab(self.game_tab, "Jogo")
        tabs.addTab(self.brain_tab, "Cérebro")
        self.settings_button = QToolButton()  # canto da barra de abas: os Ajustes
        self.settings_button.setText("⚙")
        self.settings_button.setObjectName("settings")
        self.settings_button.setToolTip("Ajustes: tempos do foco e da água, modo e tolerância.")
        self.settings_button.setAccessibleName("Ajustes")
        self.settings_button.clicked.connect(self.open_settings)
        tabs.setCornerWidget(self.settings_button, Qt.Corner.TopRightCorner)
        # Com uma aba só, a barra repetiria o título da janela: fica escondida nesse caso.
        tabs.tabBar().setVisible(tabs.count() > 1)
        self.setCentralWidget(tabs)
        for number, index in ((1, 0), (2, 1), (3, 2)):  # Ctrl+1/2/3 (Design Brief §10)
            shortcut = QShortcut(QKeySequence(f"Ctrl+{number}"), self)
            shortcut.activated.connect(lambda i=index: tabs.setCurrentIndex(i))
        self._pet_minimum = QSize()
        self._pet_size = QSize()
        tabs.currentChanged.connect(self._on_tab_changed)

        tab = self.pet_tab
        tab.care.clicked.connect(self._pet_click)
        tab.pause.clicked.connect(self.toggle_pause)
        tab.mode_button.clicked.connect(self.toggle_mode)
        for button, action in (
            (tab.drink, "drink"),
            (tab.later, "water_later"),
            (tab.decline, "water_decline"),
            (tab.take_break, "take_break"),
            (tab.pause_now, "take_break"),
            (tab.skip, "skip"),
            (tab.postpone, "postpone"),
            (tab.decline_break, "break_decline"),
            (tab.end_break, "end_break_early"),
            *((b, f"away_{key}") for key, b in tab.away_buttons.items()),
        ):
            button.clicked.connect(lambda _=False, a=action: self.answer_habit(a))

        self._hint_of: str | None = None  # a fala que a dica do botão cobriu
        self._hint: str | None = None
        for button in (
            tab.care, tab.pause, tab.mode_button, tab.drink, tab.later, tab.decline,
            tab.take_break, tab.pause_now, tab.skip, tab.postpone, tab.decline_break,
            tab.end_break, *tab.away_buttons.values(),
        ):  # fmt: skip
            button.installEventFilter(self)  # a dica vira fala do pet, não balão do Windows
        self._say(phrases.WELCOME if first_run else phrases.GREETING, force=True)
        self._show_mood(controller.shown_mood)
        self._controller.habits.water.set_enabled(self._settings.water_enabled)
        self._refresh_habits()
        self._refresh_footer()
        self._fit_to_minimum()
        if self._settings.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._setup_tray()

        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self.tick)
        self._timer.start()

    def _pet_height(self, width: int) -> int:
        """Altura que a aba Pulso pede, com o painel e as linhas visíveis agora."""
        tab_bar = self.centralWidget().tabBar()
        tab_bar_height = 0 if tab_bar.isHidden() else tab_bar.sizeHint().height()
        return self.pet_tab.layout().totalHeightForWidth(width) + tab_bar_height

    def _fit_to_minimum(self) -> None:
        """Abre sempre no menor tamanho possível (e não deixa encolher além dele).

        O Qt não conta as quebras de linha dos textos no tamanho mínimo, então a altura sai de
        `totalHeightForWidth`, que pergunta ao layout quanto precisa numa largura dada.
        """
        width = max(self.minimumSizeHint().width(), PET_WIDTH)
        height = self._pet_height(width)
        self._pet_minimum = QSize(width, height)
        self.setMinimumSize(self._pet_minimum)
        self.resize(width, height)

    def _fit_panel(self) -> None:
        """A janela cresce ou encolhe o quanto o painel da vez pede, sem mexer no que o dono
        ajustou: cada fase tem um painel de altura diferente."""
        if not self._pet_minimum.isValid():  # ainda montando a janela
            return
        needed = self._pet_height(self._pet_minimum.width())
        delta = needed - self._pet_minimum.height()
        if delta == 0:
            return
        self._pet_minimum = QSize(self._pet_minimum.width(), needed)
        if self._pet_size.isValid():  # tamanho a restaurar ao voltar do Cérebro
            self._pet_size.setHeight(max(self._pet_size.height() + delta, needed))
        if self.tabs.currentWidget() is self.pet_tab:
            target = max(self.height() + delta, needed)  # antes: subir o mínimo já cresce a janela
            self.setMinimumSize(self._pet_minimum)
            self.resize(self.width(), target)

    def _on_tab_changed(self, index: int) -> None:
        """A aba Cérebro precisa de mais espaço que o pet: a janela cresce ao abri-la e volta ao
        tamanho de antes ao voltar para o Pet (o pet continua abrindo compacto)."""
        if self.tabs.widget(index) is self.brain_tab:
            self._pet_size = self.size()
            self.setMinimumSize(BRAIN_MINIMUM)
            self.resize(self.size().expandedTo(BRAIN_PREFERRED))
            self.brain_tab.refresh()
        else:
            self.setMinimumSize(self._pet_minimum)
            if self._pet_size.isValid():
                self.resize(self._pet_size)

    # ---- laço de 1 s -------------------------------------------------------------------------

    def tick(self) -> None:
        """Uma volta do laço (o `QTimer` chama; os testes também)."""
        result = self._controller.tick()
        self._on_habit_tick(self._controller.tick_habits())  # também pausado: é independente
        self._refresh_habits()
        if result is None:  # pausado: o controlador não leu nada
            return
        self.brain_tab.refresh()  # não faz nada se escondida ou congelada
        self._sync_mood()
        if result.mood_changed and result.mood is not None and not self._was_nervous:
            self._say(phrases.mood_phrase(result.mood, self._rng))

    # ---- hábitos (ciclo do foco e água) ------------------------------------------------------

    _SHOWN = {
        kinds.SHOW_WATER: phrases.ASK_WATER,
        kinds.SHOW_BREAK: phrases.ASK_BREAK,
    }

    def _shown_text(self, signal: str, tick) -> str:
        if signal == kinds.SHOW_ASK_BACK:
            cycle = self._controller.habits.cycle
            return phrases.away_question(round(cycle.last_absence_s / 60))
        if signal == kinds.SHOW_BACK:  # o descanso acabou: se passou do tempo, conta quanto
            done = tick.summary
            if done is not None and done.excess_s:
                return phrases.break_summary(done.planned_s, done.excess_s)
            return phrases.BACK_TO_WORK
        return self._SHOWN[signal]

    def _on_habit_tick(self, tick) -> None:
        for signal in tick.shown:
            text = self._shown_text(signal, tick)
            self._say(text, force=True)
            if self._tray is not None:
                self._tray.notify(text)
        if tick.recorded:  # uma omissão pode ter deixado o pet nervoso
            self._sync_mood()
            self._refresh_footer()

    def answer_habit(self, action: str) -> None:
        """O dono respondeu a uma pergunta (ou tocou em "Bebi", "Pausar agora"...)."""
        tick = self._controller.answer_habit(action)
        if action == "drink":
            self.pet_tab.pet.drink()  # o pet bebe junto, com o copo esvaziando
        text = self._reply_text(action, tick)
        if text is not None and not self._controller.habits.nervous:
            self._say(text, force=True)
        self._refresh_habits()
        self._refresh_footer()
        self._sync_mood()

    @staticmethod
    def _reply_text(action: str, tick) -> str | None:
        recorded = tick.recorded
        if action == "drink":
            return phrases.DRANK
        if action in ("water_later", "postpone"):
            return phrases.LATER_AGAIN if recorded else None
        if action in ("water_decline", "break_decline"):
            return phrases.NO_PROBLEM if recorded else None
        if action.startswith("away_") or action == "end_break_early":
            done = tick.summary
            if done is not None and done.category == kinds.CAT_PAUSE:
                return phrases.break_summary(done.planned_s, done.excess_s)
            category = action.removeprefix("away_")
            return phrases.AWAY_REPLIES.get(category, phrases.RESTED) if recorded else None
        return None  # "Pausar agora" e "Pular fase": quem fala é a virada de fase

    def toggle_mode(self) -> None:
        casual = self._controller.habits.mode is Mode.CASUAL
        self.set_mode(Mode.PROFESSIONAL if casual else Mode.CASUAL)

    def set_mode(self, mode: Mode) -> None:
        """Troca o modo (pílula ou bandeja) e guarda a escolha em Ajustes."""
        if mode is self._controller.habits.mode:
            return
        self._settings = replace(self._settings, mode=mode.value)
        self._save_settings(self._settings)
        self._switch_mode(mode)

    def _switch_mode(self, mode: Mode) -> None:
        self._controller.set_mode(mode)
        self._say(phrases.CASUAL_ON if mode is Mode.CASUAL else phrases.PROFESSIONAL_ON, force=True)
        self._refresh_habits()

    def _refresh_footer(self) -> None:
        """O placar do dia (consulta o banco: só quando algo foi gravado)."""
        habits = self._controller.habits
        left = _plural(habits.breaks_today(), "pausa", "pausas")
        postponed = habits.postponed_today()
        if postponed:
            left += f" · prorrogou {postponed}×"
        self.pet_tab.footer_left.setText(left)
        cups = _plural(habits.cups_today(), "copo", "copos")
        focus = _plural(habits.pomodoros_today(), "foco", "focos")
        self.pet_tab.footer_right.setText(f"{cups} · {focus} hoje")

    def _refresh_habits(self) -> None:
        """Põe na tela a fase do ciclo: estado, painel, cronômetro, anel e rosto."""
        habits = self._controller.habits
        cycle = habits.cycle
        tab = self.pet_tab
        c = self._colors
        phase = cycle.phase
        left = _mmss(cycle.remaining_s)
        number, total = cycle.focus_number, cycle.focus_total
        panel, dim, countdown = "timer", False, None
        ring: tuple[float, str, bool] | None = (cycle.progress, c["focus"], False)
        caption, value = f"Foco · {number} de {total}", left
        if phase is Phase.OFF:
            state, color, ring = "MODO CASUAL", c["idle"], None
            water = habits.water.remaining_s
            caption = "Água · próximo lembrete"
            value = "desligada" if water is None else f"{math.ceil(water / 60)} min"
        elif phase is Phase.WAITING:
            state, color = "AGUARDANDO VOCÊ", c["idle"]
            caption, value = "Foco · aguardando você mexer", _mmss(habits.cfg.focus_min * 60)
        elif phase is Phase.FOCUS:
            state, color = "FOCO", c["focus"]
        elif phase is Phase.AWAY:
            state, color, caption = "FOCO PARADO", c["idle"], "Foco parado · você está longe"
        elif phase is Phase.MEETING:
            state, color, dim = "EM REUNIÃO", c["meeting"], True
            caption, ring = (
                f"Foco pausado · {number} de {total}",
                (cycle.progress, c["meeting"], True),
            )
        elif phase is Phase.ASKING_BACK:
            state, color, panel, ring = "VOLTOU · O QUE FOI?", c["focus"], "away", None
            tab.away_title.setText(phrases.away_question(round(cycle.last_absence_s / 60)))
            tab.away_hint.setText(
                "Sem resposta, conto como pausa. Necessidade nunca me deixa nervoso."
            )
        elif phase is Phase.REMINDER:
            state, color, panel = "LEMBRETE", c["alert"], "reminder"
            ring = (1.0, c["alert"], False)
            tab.reminder_title.setText(
                phrases.remind_break(round(cycle.worked_s / 60), round(cycle.planned_break_s / 60))
            )
            tab.reminder_hint.setText("Pausa no horário: o Pulso aprende que acertou.")
        elif phase is Phase.BREAK:
            state = "DESCANSO LONGO" if cycle.long_break else "DESCANSANDO"
            color, panel, countdown = c["rest"], "rest", left
            ring = (cycle.progress, c["rest"], False)
            tab.rest_label.setText("Mexer no computador não encerra o descanso.")
        else:  # BREAK_OVER
            state, color, panel = "ALÉM DO DESCANSO", c["rest"], "rest"
            countdown, ring = f"+{_mmss(cycle.excess_s)}", (1.0, c["rest"], False)
            tab.rest_label.setText(
                f"{int(cycle.excess_s // 60)} min além. O foco volta quando você mexer."
            )
        tab.set_state(state, color)
        tab.show_timer(caption, value, dim=dim, buttons=phase is Phase.FOCUS)
        tab.show_mode(habits.mode)
        if ring is None:
            tab.pet.clear_ring()
        else:
            tab.pet.set_ring(*ring)
        tab.pet.rest(countdown)  # descansa e mostra a contagem
        water_asking = habits.asking == "water"
        tab.show_panel(panel)
        tab.show_asking(water_asking)
        if phase is not self._phase:
            self._narrate(self._phase, phase)
            self._phase = phase
        if (panel, water_asking) != self._layout_key:
            self._layout_key = (panel, water_asking)
            self._fit_panel()

    def _narrate(self, old: Phase, new: Phase) -> None:
        """O pet conta as viradas de fase que não trazem aviso próprio. As que o dono provocou
        (modo, resposta) já falaram; aqui ficam reunião, descanso e a volta à reunião."""
        cycle = self._controller.habits.cycle
        if new is Phase.MEETING:
            self._say(phrases.MEETING_ON)
        elif old is Phase.MEETING and new is Phase.FOCUS:
            self._say(phrases.MEETING_OFF)
        elif new is Phase.BREAK:
            text = phrases.LONG_BREAK_STARTED if cycle.long_break else phrases.BREAK_STARTED
            self._say(text, force=True)

    def _sync_mood(self) -> None:
        """Põe no rosto o humor que vale agora ("nervoso" vence o da rede) e fala na virada."""
        habits = self._controller.habits
        nervous = habits.nervous
        if not self._controller.paused:
            self._show_mood(self._controller.shown_mood)
        if nervous and not self._was_nervous:
            self._say(phrases.nervous_phrase(habits.nervous_reason), force=True)
        elif self._was_nervous and not nervous:
            self._say(phrases.RELAXED, force=True)
        self._was_nervous = nervous

    # ---- botões ------------------------------------------------------------------------------

    def _pet_click(self) -> None:
        """Carinho: o Pulso só reage (não há mais bronca, ver doc 06, etapa 7)."""
        pet = self.pet_tab.pet
        pet.burst("💚")  # retorno visual imediato
        pet.react("contente")  # depois, volta ao humor
        self._controller.owner_reward(+1)
        self._say(phrases.PETTED, force=True)

    def toggle_pause(self) -> None:
        if self._controller.paused:
            self._controller.resume()
            self._show_mood(self._controller.shown_mood)
            self._say(phrases.RESUMED, force=True)
        else:
            self._controller.pause()
            self._show_mood(phrases.SLEEPING)
            self._say(phrases.PAUSED, force=True)
        self.pet_tab.show_paused(self._controller.paused)

    def _show_mood(self, mood: str | None) -> None:
        """Põe o humor no rosto e escreve embaixo o que ele significa."""
        self.pet_tab.pet.set_mood(mood)
        self.game_tab.face.set_mood(mood)  # o rosto da aba Jogo acompanha o humor
        if mood == phrases.SLEEPING:
            meaning = phrases.MEANING_SLEEPING
        elif mood == "nervoso":
            meaning = phrases.nervous_meaning(self._controller.habits.nervous_reason)
        else:
            meaning = phrases.MOOD_MEANINGS.get(mood, phrases.MEANING_NEW)
        self.pet_tab.caption.setText(meaning)
        self.pet_tab.pet.setToolTip(f"{meaning}\n{phrases.MEANING_HINT}")

    # ---- fala --------------------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (nome do Qt)
        """Passar o mouse num botão faz o pet dizer o que ele faz; sair devolve a fala de antes."""
        kind = event.type()
        if kind == QEvent.Type.ToolTip and isinstance(obj, QPushButton):
            return True  # a dica é a fala do pet, sem o balão padrão do Windows
        if kind == QEvent.Type.Enter and isinstance(obj, QPushButton) and obj.toolTip():
            speech = self.pet_tab.speech
            if self._hint is None or speech.text() != self._hint:
                self._hint_of = speech.text()
            self._hint = obj.toolTip()
            speech.setText(self._hint)
        elif kind == QEvent.Type.Leave and self._hint is not None:
            speech = self.pet_tab.speech
            if speech.text() == self._hint and self._hint_of is not None:
                speech.setText(self._hint_of)  # só desfaz se ninguém falou nesse meio-tempo
            self._hint = self._hint_of = None
        return super().eventFilter(obj, event)

    def _say(self, text: str, force: bool = False) -> None:
        """Mostra uma fala. Sem `force`, respeita a retenção da fala de boas-vindas."""
        if not force and self._clock.now() < self._hold_until:
            return
        if force:
            self._hold_until = 0.0
        self.pet_tab.speech.setText(text)

    # ---- bandeja e opções de janela ----------------------------------------------------------

    def _setup_tray(self) -> None:
        """Monta o menu da bandeja (T05). Itens que mudam de texto são atualizados ao abrir."""
        tray = self._tray
        if tray is None:
            return
        tray.on_click(self.bring_to_front)  # clicar no aviso traz o pet para a frente
        tray.on_open(self.bring_to_front)
        tray.add_action("Mostrar o Pulso", self.bring_to_front)
        tray.menu.addSeparator()
        self._act_front = tray.add_action(
            "Sempre à frente", self.set_always_on_top, True, self._settings.always_on_top
        )
        self._act_water = tray.add_action(
            "Lembrete de água", self.set_water_enabled, True, self._settings.water_enabled
        )
        self._act_casual = tray.add_action(
            "Modo casual",
            lambda on: self.set_mode(Mode.CASUAL if on else Mode.PROFESSIONAL),
            True,
            self._controller.habits.mode is Mode.CASUAL,
        )
        self._act_autostart = None
        if self._autostart is not None:
            self._act_autostart = tray.add_action(
                "Iniciar com o Windows", self.set_autostart, True, self._autostart.enabled()
            )
        tray.add_action("Ajustes…", self.open_settings)
        tray.menu.addSeparator()
        self._act_pause = tray.add_action("Pausar observação", self.toggle_pause)
        focus = tray.add_submenu("Foco")
        self._act_break = tray.add_action(
            "Pausar agora", lambda: self.answer_habit("take_break"), menu=focus
        )
        self._act_skip = tray.add_action(
            "Pular fase", lambda: self.answer_habit("skip"), menu=focus
        )
        tray.menu.addSeparator()
        tray.add_action("Sair do Pulso", self.quit_app)
        tray.menu.aboutToShow.connect(self._refresh_tray_menu)
        self._refresh_tray_menu()
        tray.show()

    def _refresh_tray_menu(self) -> None:
        habits = self._controller.habits
        phase = habits.cycle.phase
        self._act_pause.setText(
            "Retomar observação" if self._controller.paused else "Pausar observação"
        )
        self._act_break.setEnabled(phase in (Phase.FOCUS, Phase.REMINDER))
        self._act_skip.setEnabled(
            phase in (Phase.FOCUS, Phase.REMINDER, Phase.BREAK, Phase.BREAK_OVER)
        )
        self._act_casual.setChecked(habits.mode is Mode.CASUAL)
        if self._act_autostart is not None:  # o registro do Windows é a fonte da verdade
            self._act_autostart.setChecked(self._autostart.enabled())

    def open_settings(self) -> None:
        """Abre a tela de Ajustes; ao salvar, grava e aplica na hora."""
        self.bring_to_front()
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            self.apply_settings(dialog.settings())

    def apply_settings(self, settings: Settings) -> None:
        """Guarda os Ajustes e aplica sem reiniciar: tempos, tolerância, modo e regras."""
        self._settings = settings
        self._save_settings(settings)
        self._controller.habits.apply_config(habit_config(settings))
        self._controller.set_auto_rules(settings.auto_rules)
        mode = Mode(settings.mode)
        if mode is not self._controller.habits.mode:
            self._switch_mode(mode)
        self._refresh_habits()

    def set_always_on_top(self, on: bool) -> None:
        """Liga ou desliga "sempre à frente" e guarda a escolha."""
        self._settings = replace(self._settings, always_on_top=on)
        self._save_settings(self._settings)
        was_visible = self.isVisible()  # trocar a flag esconde a janela, então olhe antes
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        if was_visible:
            self.show()

    def set_water_enabled(self, on: bool) -> None:
        """Liga ou desliga o lembrete de água e guarda a escolha."""
        self._settings = replace(self._settings, water_enabled=on)
        self._save_settings(self._settings)
        self._controller.habits.water.set_enabled(on)
        self._refresh_habits()

    def set_autostart(self, on: bool) -> None:
        """Liga ou desliga "Iniciar com o Windows". Se o Windows recusar, avisa e desfaz o ✔."""
        try:
            self._autostart.set_enabled(on)
        except OSError:
            self._act_autostart.setChecked(not on)
            self._say("Não consegui mudar o início com o Windows.", force=True)

    def quit_app(self) -> None:
        """Sair de verdade: guarda o cérebro, tira o ícone da bandeja e encerra o programa."""
        self._quitting = True
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def prepare_to_quit(self) -> None:
        """O Windows está encerrando a sessão: não pode ficar "só escondido" no X."""
        self._quitting = True

    def bring_to_front(self) -> None:
        """Mostra a janela do pet (ao clicar numa notificação)."""
        self.tabs.setCurrentWidget(self.pet_tab)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ---- fechar ------------------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (nome do Qt)
        if not self._quitting and self._tray is not None and self._tray.available:
            event.ignore()  # o X não encerra: o pet segue na bandeja, com os avisos
            self.hide()
            if not self._told_tray:
                self._told_tray = True
                self._tray.notify(phrases.IN_TRAY)
            return
        self._timer.stop()
        self._controller.shutdown()  # guarda o cérebro
        if self._tray is not None:
            self._tray.dispose()
        super().closeEvent(event)
