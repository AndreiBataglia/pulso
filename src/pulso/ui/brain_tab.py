"""Aba "Cérebro" (T02 do Design Brief): a rede funcionando, ao vivo, para aprender vendo.

Cinco gráficos (pyqtgraph) e um rodapé:

1. **Raster** — um ponto por pulso (linha = neurônio, coluna = tempo de rede).
2. **Potencial** — a voltagem de 3 neurônios, subindo, vazando e disparando.
3. **Dopamina** — cada recompensa entregue, com a cor de quem a deu (dono ou regra automática).
4. **Humor** — quantos pulsos cada grupo de saída deu na última decisão.
5. **Pesos** — o mapa de calor da camada oculta → saída (onde o aprendizado fica escrito).

**Custo zero escondida:** a aba não tem relógio próprio. Quem a atualiza é o laço de 1 s da janela
(`refresh`), e `refresh` não faz nada se a aba está oculta (outra aba ou janela minimizada) ou
congelada: nem tira a fotografia da rede. Ao reaparecer, desenha na hora.
"""

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from pulso.brain.engine import BrainSnapshot
from pulso.clock import Clock
from pulso.controller import PetController
from pulso.ui.theme import LIGHT, MOOD_COLORS, Palette

VOLTAGE_MS = 500  # o potencial mostra só o final do registro: em 2 s os picos viram uma parede
DOPAMINE_WINDOW_S = 600.0  # o gráfico de dopamina mostra os últimos 10 min reais
DOPAMINE_RANGE = 2.0  # d = r − r̄ fica entre −2 e +1 com as recompensas de ±1
SOURCE_COLORS = {"dono": "#3CC6B5", "regra": "#E8A33D"}  # quem entregou a dopamina
LAYER_COLORS = {"entrada": "#8A8F98", "oculta_exc": "#4C8DFF", "oculta_inib": "#E5534B"}
VOLTAGE_COLORS = ("#4C8DFF", "#E5534B", "#7BD389")  # na ordem de `snapshot.voltage_labels`

HELP = {
    "raster": (
        "Raster de pulsos: cada ponto é um pulso (disparo) de um neurônio. Cada linha é um "
        "neurônio; o tempo corre da esquerda para a direita.\n\n"
        "Cinza = entrada (os sensores virando pulsos) · azul = oculta excitatória · "
        "vermelho = oculta inibitória · cores dos humores = a saída.\n\n"
        "O tempo é o da rede, que simula 100 ms a cada segundo real: o trecho mostrado "
        "costura vários segundos reais. Quando a rede aprende, o grupo do humor "
        "recompensado passa a pulsar mais nos contextos parecidos."
    ),
    "voltage": (
        "Potencial de membrana de 3 neurônios: o neurônio acumula carga a cada pulso que "
        "recebe, vaza sozinho de volta ao repouso e, ao cruzar o limiar (linha tracejada), "
        "dispara — o pico — e recomeça do repouso."
    ),
    "dopamine": (
        "Dopamina: cada barra é uma recompensa entregue à rede (últimos 10 min). Verde-água = "
        "carinho ou resposta do dono; âmbar = regra automática (ex.: voltou do ócio).\n\n"
        "Acima de zero reforça o que a rede fez há pouco; abaixo, desfaz. A barra é o "
        "'erro de previsão' (recompensa − o que já se esperava): recompensas repetidas "
        "vão ficando menores, porque deixam de ser surpresa."
    ),
    "mood": (
        "Palpite da rede: quantos pulsos cada grupo de saída deu na última janela de decisão "
        "(10 s). O rosto do Pulso NÃO segue este gráfico: ele segue regras claras (pendência, "
        "prorrogação, tempo parado, cumpriu). A rede segue aprendendo com as suas respostas; "
        "na próxima fatia, estes grupos passam a decidir o momento de lembrar."
    ),
    "weights": (
        "Pesos da camada oculta → saída: cada quadrado é uma sinapse (horizontal = neurônio "
        "oculto; vertical = neurônio de saída, agrupados por humor). Mais claro = sinapse "
        "mais forte.\n\n"
        "Marque 'Mostrar só o que mudou' para ver a diferença em relação a quando o app "
        "abriu: verde-água = ficou mais forte, vermelho = ficou mais fraca. É aqui que o "
        "aprendizado fica escrito."
    ),
}

BRAIN_PREFERRED = QSize(520, 760)  # tamanho que a janela ganha ao abrir esta aba
BRAIN_MINIMUM = QSize(420, 700)  # abaixo disto os eixos dos gráficos seriam cortados


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))


class HelpButton(QToolButton):
    """O ❓ ao lado do título de cada gráfico. Passar o mouse mostra a dica; clicar também (para
    funcionar pelo teclado e em telas sensíveis ao toque)."""

    def __init__(self, text: str, title: str) -> None:
        super().__init__()
        self.help_text = text
        self.setText("❓")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text)
        self.setAccessibleName(f"Ajuda: {title}")
        self.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), text, self))


class BrainTab(QWidget):
    def __init__(
        self,
        controller: PetController,
        clock: Clock,
        palette: Palette = LIGHT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._clock = clock
        self._palette = palette
        self._frozen = False
        self._reference_weights = controller.snapshot().weights.copy()  # de quando o app abriu
        self.refresh_count = 0  # quantas vezes desenhou (os testes conferem que oculta não conta)

        # ---- topo: título e congelar ----
        self.freeze = QPushButton("Congelar")
        self.freeze.setToolTip(
            "Para os gráficos para você olhar com calma. A rede continua rodando."
        )
        self.freeze.clicked.connect(self.toggle_freeze)
        top = QHBoxLayout()
        title = QLabel("Cérebro ao vivo")
        title.setObjectName("brain_title")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.freeze)

        # ---- gráficos ----
        self.raster = self._plot(120)
        self.voltage = self._plot(100)
        self.dopamine = self._plot(70)
        self.mood = self._plot(80)
        self.weights = self._plot(100)
        self._build_raster()
        self._build_voltage()
        self._build_dopamine()
        self._build_mood()
        self._build_weights()

        self.only_changes = QCheckBox("Mostrar só o que mudou")
        self.only_changes.setToolTip("Compara os pesos com os de quando o app abriu.")
        self.only_changes.toggled.connect(lambda _: self._draw_weights(self._last_snapshot))
        self._last_snapshot: BrainSnapshot = controller.snapshot()

        self.footer = QLabel()
        self.footer.setObjectName("caption")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.addLayout(top)
        for key, label, plot, stretch in (
            ("raster", "Raster de pulsos", self.raster, 5),
            ("voltage", "Potencial dos neurônios", self.voltage, 4),
            ("dopamine", "Dopamina", self.dopamine, 3),
            ("mood", "Palpite da rede (pulsos por grupo)", self.mood, 4),
            ("weights", "Pesos oculta → saída", self.weights, 5),
        ):
            row = self._heading(label, HELP[key])
            if key == "weights":
                row.addStretch()
                row.addWidget(self.only_changes)
            layout.addLayout(row)
            layout.addWidget(plot, stretch=stretch)
        layout.addWidget(self.footer)
        self.refresh(force=True)

    # ---- construção ---------------------------------------------------------------------------

    def _heading(self, text: str, help_text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)
        label = QLabel(text)
        label.setObjectName("caption")
        row.addWidget(label)
        row.addWidget(HelpButton(help_text, text))
        return row

    def _plot(self, min_height: int) -> pg.PlotWidget:
        p = self._palette
        plot = pg.PlotWidget(background=p.surface)
        plot.setMinimumHeight(min_height)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(False, False)  # só mostrar: nada de zoom acidental
        plot.hideButtons()
        for name in ("left", "bottom"):
            axis = plot.getAxis(name)
            axis.setPen(p.text_secondary)
            axis.setTextPen(p.text_secondary)
            axis.enableAutoSIPrefix(False)  # sem "(x0.001)": os rótulos já trazem a unidade
        return plot

    def _build_raster(self) -> None:
        self.raster.setLabel("bottom", "tempo da rede (s)")
        self.raster.getAxis("left").setTicks([[]])  # neurônios sem número: o que importa é a camada
        self.raster.setYRange(0, 1, padding=0)
        self._scatters: dict[str, pg.ScatterPlotItem] = {}
        for key in (*LAYER_COLORS, *MOOD_COLORS):
            color = LAYER_COLORS.get(key) or MOOD_COLORS[key]
            item = pg.ScatterPlotItem(size=2, pen=None, brush=pg.mkBrush(color), pxMode=True)
            self.raster.addItem(item)
            self._scatters[key] = item

    def _build_voltage(self) -> None:
        self.voltage.setLabel("bottom", "tempo da rede (s)")
        self.voltage.setLabel("left", "mV")
        self.voltage.addItem(
            pg.InfiniteLine(
                pos=-50.0,
                angle=0,
                pen=pg.mkPen(self._palette.text_secondary, style=Qt.PenStyle.DashLine),
            )
        )
        self._v_lines = [self.voltage.plot(pen=pg.mkPen(c, width=1.2)) for c in VOLTAGE_COLORS]
        self.voltage.setYRange(-70, 25, padding=0)

    def _build_dopamine(self) -> None:
        self.dopamine.setLabel("bottom", "minutos atrás")
        self.dopamine.setXRange(-DOPAMINE_WINDOW_S / 60, 0, padding=0)
        self.dopamine.setYRange(-DOPAMINE_RANGE, DOPAMINE_RANGE, padding=0)
        self.dopamine.addItem(
            pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(self._palette.text_secondary))
        )
        self._dopamine_bars = pg.BarGraphItem(x=[], height=[], width=0.12)
        self.dopamine.addItem(self._dopamine_bars)

    def _build_mood(self) -> None:
        moods = list(MOOD_COLORS)[:5]  # os 5 humores da rede ("dormindo" não é da rede)
        self.mood.invertY(True)  # o primeiro humor fica em cima
        self.mood.getAxis("left").setTicks([list(enumerate(moods))])
        self.mood.setYRange(-0.6, len(moods) - 0.4, padding=0)
        self._mood_names = moods
        self._mood_bars = pg.BarGraphItem(x0=0, y=np.arange(len(moods)), height=0.6, width=[0] * 5)
        self.mood.addItem(self._mood_bars)

    def _build_weights(self) -> None:
        self.weights.invertY(True)  # o primeiro humor fica em cima, como no gráfico de humor
        self.weights.getAxis("bottom").setStyle(showValues=False)
        self.weights.setLabel("bottom", "neurônios ocultos excitatórios")
        self._weights_image = pg.ImageItem()
        self.weights.addItem(self._weights_image)
        dark = _rgb(self._palette.background)
        teal = _rgb(SOURCE_COLORS["dono"])
        red = _rgb(LAYER_COLORS["oculta_inib"])
        self._cmap_weights = pg.ColorMap([0.0, 1.0], [dark, teal])
        self._cmap_change = pg.ColorMap([0.0, 0.5, 1.0], [red, dark, teal])

    # ---- congelar -----------------------------------------------------------------------------

    @property
    def frozen(self) -> bool:
        return self._frozen

    def toggle_freeze(self) -> None:
        self._frozen = not self._frozen
        self.freeze.setText("Continuar" if self._frozen else "Congelar")
        if not self._frozen:
            self.refresh()

    # ---- atualização --------------------------------------------------------------------------

    def refresh(self, force: bool = False) -> None:
        """Redesenha tudo com a rede de agora. Escondida ou congelada, não faz nada."""
        if not force and (self._frozen or not self.isVisible()):
            return
        self.refresh_count += 1
        snap = self._last_snapshot = self._controller.snapshot()
        self._draw_raster(snap)
        self._draw_voltage(snap)
        self._draw_dopamine()
        self._draw_mood(snap)
        self._draw_weights(snap)
        pos, neg = snap.rewards
        cost = f"{self._controller.step_cost_ms:.1f}".replace(".", ",")
        self.footer.setText(f"rede: {cost} ms por volta de 1 s · recompensas +{pos} / −{neg}")

    def showEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().showEvent(event)
        self.refresh()  # voltou a aparecer: põe os gráficos em dia

    def _time_axis(self, n: int) -> np.ndarray:
        """Segundos de rede de cada coluna, com 0 = agora."""
        return (np.arange(n) - n) / 1000.0

    def _draw_raster(self, snap: BrainSnapshot) -> None:
        n_rows, n = snap.spikes.shape
        self.raster.setXRange(-2.0, 0, padding=0)
        self.raster.setYRange(0, max(n_rows, 1), padding=0)
        times = self._time_axis(n)
        for kind, start, stop in snap.layers:
            if kind != "saida":
                self._scatters[kind].setData(*self._points(snap.spikes[start:stop], start, times))
                continue
            for g, name in enumerate(snap.groups):
                a = start + g * snap.group_size
                b = a + snap.group_size
                self._scatters[name].setData(*self._points(snap.spikes[a:b], a, times))

    @staticmethod
    def _points(block: np.ndarray, first_row: int, times: np.ndarray):
        rows, cols = np.nonzero(block)
        return times[cols], rows + first_row + 0.5

    def _draw_voltage(self, snap: BrainSnapshot) -> None:
        traces = snap.voltage[:, -VOLTAGE_MS:]
        times = self._time_axis(traces.shape[1])
        self.voltage.setXRange(-VOLTAGE_MS / 1000.0, 0, padding=0)
        for line, trace in zip(self._v_lines, traces, strict=True):
            line.setData(times, trace)

    def _draw_dopamine(self) -> None:
        now = self._clock.now()
        events = [e for e in self._controller.dopamine_events if now - e.time <= DOPAMINE_WINDOW_S]
        self._dopamine_bars.setOpts(
            x=[(e.time - now) / 60.0 for e in events],  # minutos atrás (negativo)
            height=[e.value for e in events],
            width=0.12,
            brushes=[pg.mkBrush(SOURCE_COLORS.get(e.source, "#8A8F98")) for e in events],
        )

    def _draw_mood(self, snap: BrainSnapshot) -> None:
        counts = self._controller.mood_counts()
        top = max(float(counts.max()), 1.0)
        self.mood.setXRange(0, top * 1.1, padding=0)
        self._mood_bars.setOpts(
            x0=0,
            y=np.arange(len(counts)),
            height=0.6,
            width=counts,
            brushes=[pg.mkBrush(MOOD_COLORS[m]) for m in snap.groups],
        )

    def _draw_weights(self, snap: BrainSnapshot) -> None:
        w = snap.weights
        n_pre, n_post = w.shape
        if self.only_changes.isChecked():
            delta = w - self._reference_weights
            limit = max(float(np.abs(delta).max()), 1e-6)  # centro = 0, sem mudança
            self._weights_image.setColorMap(self._cmap_change)
            self._weights_image.setImage(delta, levels=(-limit, limit), autoLevels=False)
        else:
            self._weights_image.setColorMap(self._cmap_weights)
            self._weights_image.setImage(w, levels=(0.0, snap.weights_max), autoLevels=False)
        self._weights_image.setRect(0, 0, n_pre, n_post)
        self.weights.setXRange(0, n_pre, padding=0)
        self.weights.setYRange(0, n_post, padding=0)
        centers = [
            (g * snap.group_size + snap.group_size / 2, name) for g, name in enumerate(snap.groups)
        ]
        self.weights.getAxis("left").setTicks([centers])

    # ---- tamanho ------------------------------------------------------------------------------

    def sizeHint(self) -> QSize:  # noqa: N802
        return BRAIN_PREFERRED

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        # Pequeno de propósito: a janela abre no menor tamanho e só cresce ao abrir esta aba.
        return QSize(280, 160)
