"""Janela principal: abas "Pet" e "Cérebro" e o laço de 1 s no `QTimer`.

Conceitos de Qt usados aqui:
- **Sinal e *slot***: um botão emite o sinal `clicked`; ligamos (`connect`) esse sinal a um método
  nosso (o *slot*), que o Qt chama quando o clique acontece.
- **`QTimer`**: dispara o sinal `timeout` a cada intervalo, dentro do laço de eventos do Qt, sem
  threads. A leitura do sensor e a rede custam poucos ms, então cabem na thread da interface.
"""

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
from pulso.habits.pomodoro import Phase
from pulso.storage.autostart import Autostart
from pulso.storage.config import Settings, habit_config
from pulso.storage.db import GameStore
from pulso.ui import phrases
from pulso.ui.brain_tab import BRAIN_MINIMUM, BRAIN_PREFERRED, BrainTab
from pulso.ui.game_tab import GameTab
from pulso.ui.pet_widget import PetWidget
from pulso.ui.settings_dialog import SettingsDialog
from pulso.ui.theme import LIGHT, Palette
from pulso.ui.tray import Tray

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


_TOGGLE_ICON = {"Iniciar": "▶", "Continuar": "▶", "Pausar": "⏸"}


class PetTab(QWidget):
    """T01 do Design Brief: selo, rosto, balão de fala e os botões."""

    def __init__(self, palette: Palette = LIGHT, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_color = QColor(palette.text)  # o texto do tema, não o do sistema (modo escuro)
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
        # Hábitos: "Bebi" e "Fiz a pausa" ficam sempre à mão (o Pulso não vê o copo); "Depois" e
        # "Hoje não" só aparecem enquanto um lembrete espera resposta.
        self.drink = QPushButton("💧 Bebi")
        self.rested = QPushButton("☕ Pausa")
        self.later = QPushButton("Depois")
        self.decline = QPushButton("Hoje não")
        self.pomodoro_label = QLabel()
        self.pomodoro_label.setObjectName("caption")
        self.pomodoro_toggle = QPushButton()
        self.pomodoro_skip = QPushButton("⏭")
        self.pomodoro_skip.setToolTip("Pula a fase atual do pomodoro.")
        self.pomodoro_skip.setAccessibleName("Pular fase")
        self.care.setToolTip("Um carinho: o Pulso aprende que você gostou do jeito dele.")
        self.scold.setToolTip("Uma bronca: o Pulso aprende que você não gostou.")
        self.later.setToolTip("Depois: me lembra de novo em alguns minutos.")
        self.decline.setToolTip("Hoje não: deixa passar (conta como recusa).")
        self.drink.setToolTip("Bebi água: zera o lembrete de água.")
        self.rested.setToolTip("Fiz a pausa: descansei longe da tela.")
        for mini in (
            self.drink,
            self.rested,
            self.later,
            self.decline,
            self.pomodoro_toggle,
            self.pomodoro_skip,
        ):
            mini.setObjectName("mini")  # botões secundários: menores que Carinho/Bronca

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        row.addWidget(self.care)
        row.addWidget(self.scold)
        row.addWidget(self.pause)  # ao lado dos demais, só o ícone
        row.addStretch()

        habits = QHBoxLayout()
        habits.setSpacing(8)
        habits.addStretch()
        habits.addWidget(self.drink)
        habits.addWidget(self.rested)
        habits.addStretch()
        # Linha própria (só durante um lembrete): quatro botões juntos deixariam a janela larga.
        self.ask_row = QWidget()
        asking = QHBoxLayout(self.ask_row)
        asking.setContentsMargins(0, 0, 0, 0)
        asking.setSpacing(8)
        asking.addStretch()
        asking.addWidget(self.later)
        asking.addWidget(self.decline)
        asking.addStretch()
        pomodoro = QHBoxLayout()
        pomodoro.setSpacing(8)
        pomodoro.addStretch()
        pomodoro.addWidget(self.pomodoro_label)
        pomodoro.addWidget(self.pomodoro_toggle)
        pomodoro.addWidget(self.pomodoro_skip)
        pomodoro.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignHCenter)  # só se pausado
        layout.addWidget(self.caption)  # o que o humor significa, acima do rosto
        layout.addWidget(self.pet, stretch=11)
        layout.addWidget(self.speech, stretch=2)
        layout.addLayout(row)
        layout.addLayout(habits)
        layout.addWidget(self.ask_row)
        layout.addLayout(pomodoro)
        self.show_asking(None)
        self.show_pomodoro("🍅 Parado", "Iniciar", skippable=False)
        self.show_paused(False)

    def show_asking(self, asking: str | None) -> None:
        """Os botões "Depois" e "Hoje não" só existem com um lembrete esperando resposta."""
        self.ask_row.setVisible(asking is not None)

    def ask_row_height(self) -> int:
        """Quanto a linha "Depois/Hoje não" acrescenta à janela (botão + espaçamento)."""
        return self.decline.sizeHint().height() + self.layout().spacing()

    def show_pomodoro(self, text: str, toggle: str, skippable: bool) -> None:
        self.pomodoro_label.setText(text)
        self.pomodoro_toggle.setText(_TOGGLE_ICON[toggle])
        self.pomodoro_toggle.setToolTip(toggle)
        self.pomodoro_toggle.setAccessibleName(toggle)
        self.pomodoro_skip.setEnabled(skippable)

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
        self.scold.setEnabled(not paused)


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
        self._ask_space = False  # a linha "Depois/Hoje não" está contada no tamanho da janela?
        self._clock = clock
        self._rng = rng or random.Random()
        self._hold_until = clock.now() + WELCOME_HOLD_S if first_run else 0.0

        self.pet_tab = PetTab(palette)
        self.game_tab = GameTab(scores, rng)
        self.brain_tab = BrainTab(controller, clock, palette)
        self.tabs = tabs = QTabWidget()
        tabs.addTab(self.pet_tab, "Pet")  # "Saúde" entra na etapa 7
        tabs.addTab(self.game_tab, "Jogo")
        tabs.addTab(self.brain_tab, "Cérebro")
        self.settings_button = QToolButton()  # canto da barra de abas: os Ajustes
        self.settings_button.setText("⚙")
        self.settings_button.setObjectName("settings")
        self.settings_button.setToolTip("Ajustes: tempos do pomodoro e da água.")
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

        self.pet_tab.care.clicked.connect(lambda: self._owner_click(+1))
        self.pet_tab.scold.clicked.connect(lambda: self._owner_click(-1))
        self.pet_tab.pause.clicked.connect(self.toggle_pause)
        tab = self.pet_tab
        for button, action in (
            (tab.drink, "drink"),
            (tab.rested, "rest"),
            (tab.pomodoro_skip, "skip"),
        ):
            button.clicked.connect(lambda _=False, a=action: self.answer_habit(a))
        tab.later.clicked.connect(lambda: self.answer_habit(self._ask_action("later")))
        tab.decline.clicked.connect(lambda: self.answer_habit(self._ask_action("decline")))
        tab.pomodoro_toggle.clicked.connect(self.toggle_pomodoro)

        self._hint_of: str | None = None  # a fala que a dica do botão cobriu
        self._hint: str | None = None
        for button in (
            tab.care,
            tab.scold,
            tab.pause,
            tab.drink,
            tab.rested,
            tab.later,
            tab.decline,
            tab.pomodoro_toggle,
            tab.pomodoro_skip,
        ):
            button.installEventFilter(self)  # a dica vira fala do pet, não balão do Windows
        self._say(phrases.WELCOME if first_run else phrases.GREETING, force=True)
        self._show_mood(controller.shown_mood)
        self._refresh_habits()
        self._fit_to_minimum()
        self._controller.habits.water.set_enabled(self._settings.water_enabled)
        if self._settings.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._setup_tray()

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
        tab_bar = tabs.tabBar()
        tab_bar_height = 0 if tab_bar.isHidden() else tab_bar.sizeHint().height()
        height = self.pet_tab.layout().totalHeightForWidth(width) + tab_bar_height
        self._pet_minimum = QSize(width, height)
        self.setMinimumSize(self._pet_minimum)
        self.resize(width, height)

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

    # ---- hábitos (pomodoro e água) -----------------------------------------------------------

    _SHOWN = {
        kinds.SHOW_WATER: phrases.ASK_WATER,
        kinds.SHOW_BREAK: phrases.ASK_BREAK,
        kinds.SHOW_BACK: phrases.BACK_TO_WORK,
    }
    _REPLIES = {
        kinds.WATER_DRUNK: phrases.DRANK,
        kinds.BREAK_DONE: phrases.RESTED,
        kinds.WATER_SNOOZED: phrases.LATER_AGAIN,
        kinds.BREAK_SNOOZED: phrases.LATER_AGAIN,
        kinds.WATER_DECLINED: phrases.NO_PROBLEM,
        kinds.BREAK_DECLINED: phrases.NO_PROBLEM,
    }

    def _on_habit_tick(self, tick) -> None:
        for signal in tick.shown:
            text = self._SHOWN[signal]
            self._say(text, force=True)
            if self._tray is not None:
                self._tray.notify(text)
        if tick.recorded:  # uma omissão pode ter deixado o pet nervoso
            self._sync_mood()

    def _ask_action(self, base: str) -> str:
        """ "Depois"/"Hoje não" valem para o lembrete que está na tela (água primeiro)."""
        return f"{'water' if self._controller.habits.asking == 'water' else 'break'}_{base}"

    def answer_habit(self, action: str) -> None:
        """O dono respondeu a um lembrete (ou tocou em "Bebi"/"Fiz a pausa")."""
        kind = self._controller.answer_habit(action)
        if kind == kinds.WATER_DRUNK:
            self.pet_tab.pet.drink()  # o pet bebe junto, com o copo esvaziando
        text = self._REPLIES.get(kind)
        if text is not None and not self._controller.habits.nervous:
            self._say(text, force=True)
        self._refresh_habits()
        self._sync_mood()

    def toggle_pomodoro(self) -> None:
        pomodoro = self._controller.habits.pomodoro
        if not pomodoro.running:
            pomodoro.start()
        elif pomodoro.paused:
            pomodoro.resume()
        elif pomodoro.phase in (Phase.FOCUS, Phase.BREAK):
            pomodoro.pause()
        self._refresh_habits()

    def _refresh_habits(self) -> None:
        """Atualiza o contador do pomodoro e os botões dos lembretes."""
        habits = self._controller.habits
        pomodoro = habits.pomodoro
        left = f"{int(pomodoro.remaining_s) // 60:02d}:{int(pomodoro.remaining_s) % 60:02d}"
        paused = " (pausado)" if pomodoro.paused else ""
        toggle = "Continuar" if pomodoro.paused else "Pausar"
        if pomodoro.phase is Phase.FOCUS:
            text = f"🍅 Foco {left}{paused}"
        elif pomodoro.phase is Phase.BREAK:
            kind = "longo" if pomodoro.long_break else "curto"
            text = f"🍅 Descanso{' longo' if kind == 'longo' else ''} {left}{paused}"
        elif pomodoro.phase is Phase.ASKING:
            text = "🍅 Hora de descansar"
        else:
            text, toggle = "🍅 Parado", "Iniciar"
        resting = pomodoro.phase is Phase.BREAK and not pomodoro.paused
        self.pet_tab.pet.rest(left if resting else None)  # descansa e mostra a contagem
        self.pet_tab.show_pomodoro(text, toggle, skippable=pomodoro.running)
        self.pet_tab.pomodoro_toggle.setEnabled(pomodoro.phase is not Phase.ASKING)
        self.pet_tab.show_asking(habits.asking)
        self._make_room_for_asking(habits.asking is not None)

    def _make_room_for_asking(self, asking: bool) -> None:
        """A janela cresce uma linha enquanto um lembrete espera resposta e volta depois."""
        if asking == self._ask_space:
            return
        self._ask_space = asking
        delta = self.pet_tab.ask_row_height() * (1 if asking else -1)
        self._pet_minimum = QSize(self._pet_minimum.width(), self._pet_minimum.height() + delta)
        if self._pet_size.isValid():  # tamanho a restaurar ao voltar do Cérebro
            self._pet_size.setHeight(self._pet_size.height() + delta)
        if self.tabs.currentWidget() is self.pet_tab:
            self.setMinimumSize(self._pet_minimum)
            self.resize(self.width(), self.height() + delta)

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

    def _owner_click(self, sign: int) -> None:
        pet = self.pet_tab.pet
        pet.burst("💚" if sign > 0 else "💢")  # retorno visual imediato
        pet.react("contente" if sign > 0 else "arrependido")  # depois, volta ao humor
        self._controller.owner_reward(sign)
        self._say(phrases.PETTED if sign > 0 else phrases.SCOLDED, force=True)

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
        self._act_autostart = None
        if self._autostart is not None:
            self._act_autostart = tray.add_action(
                "Iniciar com o Windows", self.set_autostart, True, self._autostart.enabled()
            )
        tray.add_action("Ajustes…", self.open_settings)
        tray.menu.addSeparator()
        self._act_pause = tray.add_action("Pausar observação", self.toggle_pause)
        pomodoro = tray.add_submenu("Pomodoro")
        self._act_pomodoro = tray.add_action("Iniciar", self.toggle_pomodoro, menu=pomodoro)
        self._act_skip = tray.add_action(
            "Pular fase", lambda: self.answer_habit("skip"), menu=pomodoro
        )
        tray.menu.addSeparator()
        tray.add_action("Sair do Pulso", self.quit_app)
        tray.menu.aboutToShow.connect(self._refresh_tray_menu)
        self._refresh_tray_menu()
        tray.show()

    def _refresh_tray_menu(self) -> None:
        pomodoro = self._controller.habits.pomodoro
        self._act_pause.setText(
            "Retomar observação" if self._controller.paused else "Pausar observação"
        )
        if not pomodoro.running:
            label = "Iniciar"
        elif pomodoro.paused:
            label = "Continuar"
        else:
            label = "Pausar"
        self._act_pomodoro.setText(label)
        self._act_pomodoro.setEnabled(pomodoro.phase is not Phase.ASKING)
        self._act_skip.setEnabled(pomodoro.running)
        if self._act_autostart is not None:  # o registro do Windows é a fonte da verdade
            self._act_autostart.setChecked(self._autostart.enabled())

    def open_settings(self) -> None:
        """Abre a tela de Ajustes; ao salvar, grava e aplica na hora."""
        self.bring_to_front()
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            self.apply_settings(dialog.settings())

    def apply_settings(self, settings: Settings) -> None:
        """Guarda os Ajustes e aplica sem reiniciar: tempos dos hábitos e regras automáticas."""
        self._settings = settings
        self._save_settings(settings)
        self._controller.habits.apply_config(habit_config(settings))
        self._controller.set_auto_rules(settings.auto_rules)
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
