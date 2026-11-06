"""O rosto do pet, desenhado com QPainter (Design Brief §7.1): fundo escuro, olhos, boca e emojis.

Como a animação funciona
------------------------
Cada humor é um conjunto de **números** (abertura do olho, curva da boca, ...). O desenho sempre
usa os números *atuais*, e a cada quadro eles andam um pedaço em direção aos números do humor-alvo
(suavização exponencial). Trocar de humor, então, não "pula": o rosto escorrega de uma expressão
para a outra em ~0,4 s. Como a rede só decide o humor a cada 10 s, ele não pisca a cada segundo.

Microanimações (piscar a cada 3–6 s, olhar de lado, inclinar o rosto) dão vida; a pausa
("dormindo") desliga tudo, e o relógio de quadros para quando nada mais se mexe (zero CPU).
"""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from pulso.ui.phrases import SLEEPING
from pulso.ui.theme import FACE_BACKGROUND, MOOD_COLORS

FRAME_MS = 33  # ~30 quadros por segundo
SETTLE_S = 0.12  # constante de tempo da suavização (a troca de humor leva ~3x isto)
BLINK_S = 0.16
BURST_S = 0.9


def _look(
    eye, happy, curve, mouth_open, brow, z, drop, zzz, bounce, shake=0, angry=0
) -> dict[str, float]:
    return dict(
        eye=eye, happy=happy, curve=curve, mouth_open=mouth_open, brow=brow,
        z=z, drop=drop, zzz=zzz, bounce=bounce, shake=shake, angry=angry,
    )  # fmt: skip


# Números de cada expressão. `happy`: olho em arco (^). `brow`: sobrancelha inclinada.
# `shake`: tremor leve do rosto (nervoso e bravo). `angry`: sobrancelha inclinada para baixo.
LOOKS: dict[str, dict[str, float]] = {
    "neutro": _look(0.8, 0, 0.3, 0, 0, 0, 0, 0, 0),
    "arrependido": _look(0.5, 0, -0.4, 0, 0, 0, 0, 0, 0),  # reação à bronca
    "animado": _look(1.0, 0, 0.9, 0.9, 0, 0, 0, 0, 1),
    "contente": _look(0.9, 1, 0.8, 0, 0, 0, 0, 0, 0),
    "entediado": _look(0.4, 0, 0, 0, 0, 0, 0, 0, 0),
    "sonolento": _look(0.22, 0, 0.1, 0, 0, 1, 0, 0, 0),
    "preocupado": _look(0.9, 0, -0.5, 0, 1, 0, 1, 0, 0),
    # Nervoso (pendência de hábito): o "preocupado" com olhos mais arregalados e um leve tremor.
    "nervoso": _look(1.0, 0, -0.5, 0, 1, 0, 1, 0, 0, shake=1),
    # Bravo (perdeu o jogo): olhos estreitos, sobrancelha para baixo, boca virada e tremor.
    "bravo": _look(0.6, 0, -0.6, 0, 0, 0, 0, 0, 0, shake=0.6, angry=1),
    SLEEPING: _look(0.0, 0, 0.15, 0, 0, 0, 0, 1, 0),
    # Atividades (o dono aceitou a pausa ou bebeu água): descansando = olhos fechados e sorriso
    # calmo, respirando; bebendo = olhos em arco, contente, com um copo esvaziando.
    "descansando": _look(0.0, 0, 0.5, 0, 0, 0, 0, 1, 0),
    "bebendo": _look(0.9, 1, 0.8, 0, 0, 0, 0, 0, 0),
}
_LOOK_COLOR = dict(
    MOOD_COLORS,
    neutro=MOOD_COLORS["entediado"],
    arrependido="#A3B1C6",
    nervoso="#FF9B7A",
    bravo="#FF6B6B",
    descansando=MOOD_COLORS["sonolento"],
    bebendo="#7FD1FF",
)
DRINK_S = 15.0  # quanto o pet "bebe" depois do "Bebi"
REACTION_S = 2.5  # quanto tempo dura a reação ao carinho/bronca


def _rgb(hex_color: str) -> list[float]:
    c = QColor(hex_color)
    return [float(c.red()), float(c.green()), float(c.blue())]


def _alpha(color: QColor, weight: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(min(max(weight, 0.0), 1.0))
    return c


def _line_pen(color: QColor, thickness: float) -> QPen:
    return QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)


class PetWidget(QWidget):
    def __init__(self, rng: random.Random | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self._rng = rng or random.Random()
        self._target = "neutro"
        self._look = dict(LOOKS["neutro"])
        self._color = _rgb(_LOOK_COLOR["neutro"])
        self._t = 0.0  # tempo de animação acumulado (s)
        self._next_blink = self._rng.uniform(3, 6)
        self._blink_start: float | None = None
        self._next_gaze = self._rng.uniform(4, 9)
        self._gaze_until = 0.0
        self._gaze_x = 0.0
        self._reaction: tuple[str, float] | None = None  # (aparência, instante em que acaba)
        self._bursts: list[tuple[str, float]] = []  # (emoji, instante em que nasceu)
        self._activity: str | None = None  # "descansando" ou "bebendo" (sobre o humor da rede)
        self._drink_until = 0.0
        self._countdown: str | None = None  # texto da contagem regressiva do descanso
        self._last_frame = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._on_timer)
        self.setAccessibleName("Rosto do pet")

    # ---- estado ------------------------------------------------------------------------------

    @property
    def target(self) -> str:
        """O humor-alvo atual (`"neutro"` antes da primeira decisão da rede)."""
        return self._target

    @property
    def sleeping(self) -> bool:
        return self._target == SLEEPING

    def set_mood(self, mood: str | None) -> None:
        """Muda o humor-alvo (`None` = ainda sem decisão; `SLEEPING` = pausa)."""
        name = mood or "neutro"
        if name not in LOOKS:
            raise ValueError(f"humor desconhecido: {mood!r}")
        self._target = name
        self.setAccessibleDescription(f"Humor: {name}")
        self._ensure_timer()

    @property
    def shown(self) -> str:
        """A aparência em uso agora: reação, depois pausa de privacidade, atividade, humor."""
        if self._reaction:
            return self._reaction[0]
        if self.sleeping:  # a pausa de privacidade vence a atividade
            return self._target
        return self._activity or self._target

    @property
    def activity(self) -> str | None:
        return self._activity

    def rest(self, countdown: str | None) -> None:
        """Descanso do pomodoro: o pet descansa e mostra a contagem (`None` = acabou o descanso)."""
        if countdown is None:
            if self._activity == "descansando":
                self._activity = None
        elif self._activity != "bebendo":  # beber (15 s) não é interrompido pelo relógio
            self._activity = "descansando"
        self._countdown = countdown
        self._ensure_timer()
        self.update()

    def drink(self) -> None:
        """O dono bebeu água: o pet bebe por `DRINK_S` segundos, com o copo esvaziando."""
        self._activity = "bebendo"
        self._drink_until = self._t + DRINK_S
        self._ensure_timer()

    def react(self, look: str, seconds: float = REACTION_S) -> None:
        """Reação curta (carinho → "contente", bronca → "arrependido"): depois, volta ao humor."""
        if look not in LOOKS:
            raise ValueError(f"aparência desconhecida: {look!r}")
        self._reaction = (look, self._t + seconds)
        self._ensure_timer()

    def burst(self, emoji: str) -> None:
        """Retorno visual imediato (💚/💢): o emoji sobe e some em ~1 s."""
        self._bursts.append((emoji, self._t))
        self._ensure_timer()
        self.update()

    # ---- animação ----------------------------------------------------------------------------

    def advance(self, dt: float) -> None:
        """Anda `dt` segundos de animação (separado do relógio: os testes controlam o tempo)."""
        self._t += dt
        k = 1.0 - math.exp(-dt / SETTLE_S)
        if self._activity == "bebendo" and self._t >= self._drink_until:
            self._activity = "descansando" if self._countdown else None
        if self._reaction and self._t >= self._reaction[1]:
            self._reaction = None  # a reação acabou: o rosto volta ao humor
        for key, value in LOOKS[self.shown].items():
            self._look[key] += (value - self._look[key]) * k
        goal_color = _rgb(_LOOK_COLOR[self.shown])
        self._color = [c + (g - c) * k for c, g in zip(self._color, goal_color, strict=True)]
        self._bursts = [(e, born) for e, born in self._bursts if self._t - born < BURST_S]
        if self.sleeping:  # dormindo: sem piscar nem olhar de lado
            self._blink_start = None
            self._gaze_x = 0.0
        else:
            self._micro_animations()
        self.update()

    def _micro_animations(self) -> None:
        if self._blink_start is None and self._t >= self._next_blink:
            self._blink_start = self._t
        if self._blink_start is not None and self._t - self._blink_start > BLINK_S:
            self._blink_start = None
            self._next_blink = self._t + self._rng.uniform(3, 6)
        if self._t >= self._next_gaze:
            self._gaze_x = self._rng.choice((-1.0, 1.0))
            self._gaze_until = self._t + 1.0
            self._next_gaze = self._t + self._rng.uniform(4, 9)
        if self._gaze_x and self._t >= self._gaze_until:
            self._gaze_x = 0.0

    def _blink_factor(self) -> float:
        """1 = olho aberto, 0 = fechado no meio da piscada."""
        if self._blink_start is None:
            return 1.0
        phase = (self._t - self._blink_start) / BLINK_S  # 0 → 1
        return min(abs(2.0 * phase - 1.0), 1.0)

    def settled(self) -> bool:
        """Verdadeiro quando nada mais se mexe (só acontece dormindo e sem efeitos)."""
        if not self.sleeping or self._bursts or self._reaction:
            return False
        close = all(abs(self._look[k] - v) < 0.01 for k, v in LOOKS[SLEEPING].items())
        goal_color = _rgb(_LOOK_COLOR[SLEEPING])
        return close and all(abs(c - g) < 1.0 for c, g in zip(self._color, goal_color, strict=True))

    @property
    def animating(self) -> bool:
        """O relógio de quadros está ligado?"""
        return self._timer.isActive()

    def _ensure_timer(self) -> None:
        if self.isVisible() and not self._timer.isActive():
            self._last_frame = time.monotonic()
            self._timer.start()

    def _on_timer(self) -> None:
        now = time.monotonic()
        self.advance(min(now - self._last_frame, 0.25))
        self._last_frame = now
        if self.settled():
            self._timer.stop()  # nada se mexe: o relógio de quadros descansa

    def showEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().showEvent(event)
        self._ensure_timer()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()  # janela minimizada ou aba oculta: não gasta CPU
        super().hideEvent(event)

    # ---- desenho -----------------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        width = max(min(w - 16, (h - 16) * 4 / 3), 1.0)
        height = width * 3 / 4
        face = QRectF((w - width) / 2, (h - height) / 2, width, height)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(FACE_BACKGROUND))
        p.drawRoundedRect(face, width * 0.12, width * 0.12)

        look = self._look
        color = QColor(*(int(round(c)) for c in self._color))
        bounce = -abs(math.sin(self._t * 5.0)) * height * 0.04 * look["bounce"]
        tilt = 0.0 if self.sleeping else math.sin(self._t * 0.7) * 2.0
        if self.shown == "descansando":  # respira devagar
            bounce += math.sin(self._t * 1.3) * height * 0.012
            tilt = 0.0
        tremor = math.sin(self._t * 47.0) * width * 0.004 * look["shake"]  # trêmulo, sem exagero
        p.save()
        p.translate(face.center().x() + tremor, face.center().y() + bounce)
        p.rotate(tilt)
        self._draw_eyes(p, color, width, height, look)
        self._draw_mouth(p, color, width, height, look)
        p.restore()
        self._draw_extras(p, face, look)
        self._draw_activity(p, face)
        self._draw_bursts(p, face)
        p.end()

    def _draw_eyes(self, p: QPainter, color: QColor, width: float, height: float, look) -> None:
        gaze = self._gaze_x * width * 0.03
        eye_w, eye_h_max = width * 0.15, height * 0.30
        eye_h = eye_h_max * look["eye"] * self._blink_factor()
        open_weight = 1.0 - look["happy"]
        for side in (-1, 1):
            cx, cy = side * width * 0.2 + gaze, -height * 0.08
            if look["happy"] > 0.01:  # olho em arco ^
                p.setPen(_line_pen(_alpha(color, look["happy"]), width * 0.025))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawArc(QRectF(cx - eye_w / 2, cy - eye_w / 4, eye_w, eye_w / 2), 0, 180 * 16)
            if open_weight > 0.01:
                if eye_h < 3:  # fechado: uma linha
                    p.setPen(_line_pen(_alpha(color, open_weight), width * 0.02))
                    p.drawLine(QPointF(cx - eye_w / 2, cy), QPointF(cx + eye_w / 2, cy))
                else:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(_alpha(color, open_weight))
                    rect = QRectF(cx - eye_w / 2, cy - eye_h / 2, eye_w, eye_h)
                    p.drawRoundedRect(rect, eye_w / 2, eye_w / 2)
            if look["angry"] > 0.01:  # sobrancelha para baixo no meio (bravo)
                p.setPen(_line_pen(_alpha(color, look["angry"]), width * 0.022))
                y0 = cy - eye_h_max * 0.75
                p.drawLine(
                    QPointF(cx - side * eye_w / 2, y0 + height * 0.05),  # dentro, mais baixa
                    QPointF(cx + side * eye_w / 2, y0 - height * 0.015),
                )
            if look["brow"] > 0.01:  # sobrancelha inclinada para o centro (preocupado)
                p.setPen(_line_pen(_alpha(color, look["brow"]), width * 0.02))
                y0 = cy - eye_h_max * 0.75
                p.drawLine(
                    QPointF(cx - side * eye_w / 2, y0 - height * 0.01),  # dentro, mais alta
                    QPointF(cx + side * eye_w / 2, y0 + height * 0.05),
                )

    def _draw_mouth(self, p: QPainter, color: QColor, width: float, height: float, look) -> None:
        my, half = height * 0.22, width * 0.09
        curve = look["curve"] * height * 0.10
        path = QPainterPath(QPointF(-half, my))
        path.quadTo(QPointF(0, my + curve * 2), QPointF(half, my))
        if look["mouth_open"] > 0.05:  # boca aberta (preenchida) quando está animado
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_alpha(color, look["mouth_open"]))
            p.drawPath(path)
        p.setPen(_line_pen(color, width * 0.02))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def _draw_extras(self, p: QPainter, face: QRectF, look) -> None:
        font = QFont("Segoe UI Emoji")
        font.setPixelSize(max(int(face.height() * 0.12), 8))
        p.setFont(font)
        float_y = math.sin(self._t * 2.0) * face.height() * 0.02
        right = face.right() - face.width() * 0.18
        top = face.top() + face.height() * 0.2
        extras = (
            (look["z"], "💤", right, top),
            (look["zzz"], "💤", right, top),
            (
                look["drop"],
                "💧",
                face.left() + face.width() * 0.14,
                face.top() + face.height() * 0.28,
            ),
        )
        for weight, emoji, x, y in extras:
            if weight > 0.02:
                p.setPen(_alpha(QColor("white"), weight))
                p.drawText(QPointF(x, y + float_y), emoji)

    def _draw_activity(self, p: QPainter, face: QRectF) -> None:
        """Copo esvaziando (bebendo) e a contagem regressiva do descanso, sobre o rosto."""
        if self.sleeping:
            return
        if self._activity == "bebendo":
            left = min(max((self._drink_until - self._t) / DRINK_S, 0.0), 1.0)
            gw, gh = face.width() * 0.13, face.height() * 0.26
            gx = face.right() - gw * 1.7
            gy = face.bottom() - gh * 1.3
            water = QRectF(gx + 2, gy + gh * (1 - left) + 1, gw - 4, gh * left - 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(127, 209, 255, 200))
            p.drawRect(water)
            p.setPen(_line_pen(QColor(220, 235, 245), face.width() * 0.012))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(gx, gy, gw, gh), 3, 3)
        if self._countdown and self._activity == "descansando":
            font = QFont("Segoe UI")
            font.setPixelSize(max(int(face.height() * 0.11), 9))
            p.setFont(font)
            p.setPen(_alpha(QColor("white"), 0.75))
            top = face.bottom() - face.height() * 0.2
            box = QRectF(face.left(), top, face.width(), face.height() * 0.14)
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, self._countdown)

    def _draw_bursts(self, p: QPainter, face: QRectF) -> None:
        font = QFont("Segoe UI Emoji")
        font.setPixelSize(max(int(face.height() * 0.16), 10))
        p.setFont(font)
        for emoji, born in self._bursts:
            age = (self._t - born) / BURST_S  # 0 → 1
            p.setPen(_alpha(QColor("white"), 1.0 - age))
            x = face.center().x() - face.width() * 0.04
            p.drawText(QPointF(x, face.top() + face.height() * (0.9 - 0.5 * age)), emoji)
