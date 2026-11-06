"""Paleta do Design Brief §3, em claro e escuro, e a conferência de contraste (WCAG)."""

from dataclasses import dataclass

# Cor do rosto por humor (a mesma nos dois temas: o rosto tem fundo escuro próprio).
MOOD_COLORS = {
    "animado": "#FFB347",
    "contente": "#7BD389",
    "entediado": "#A3B1C6",
    "sonolento": "#B59CE6",
    "preocupado": "#F28C8C",
    "dormindo": "#8A8F98",
}
FACE_BACKGROUND = "#0E1014"


@dataclass(frozen=True)
class Palette:
    background: str
    surface: str
    text: str
    text_secondary: str
    primary: str
    on_primary: str  # texto sobre um botão primário
    success: str
    warning: str
    error: str


# Primária clara: #0D7F74 (e não #0F8A7E do rascunho) para o texto branco do botão passar de 4,5:1.
LIGHT = Palette(
    "#F7F7F5",
    "#FFFFFF",
    "#1F2328",
    "#59636E",
    "#0D7F74",
    "#FFFFFF",
    "#1A7F37",
    "#9A6700",
    "#CF222E",
)
DARK = Palette(
    "#16181D",
    "#20232A",
    "#E6EDF3",
    "#9198A1",
    "#3CC6B5",
    "#0B1F1C",
    "#3FB950",
    "#D29922",
    "#F85149",
)


def _linear(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: str, b: str) -> float:
    """Razão de contraste WCAG entre duas cores `#RRGGBB` (de 1 a 21)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def stylesheet(p: Palette) -> str:
    """Folha de estilo Qt do app inteiro."""
    return f"""
    QWidget {{ background: {p.background}; color: {p.text};
        font-family: 'Segoe UI'; font-size: 13px; }}
    QTabWidget::pane {{ border: 0; }}
    QTabBar::tab {{ padding: 8px 16px; color: {p.text_secondary}; background: {p.background}; }}
    QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.primary}; }}
    QLabel#speech {{ background: {p.surface}; border: 1px solid {p.text_secondary};
        border-radius: 12px; padding: 12px; font-size: 15px; }}
    QLabel#badge {{ background: {p.surface}; border: 1px solid {p.primary}; color: {p.text};
        border-radius: 12px; padding: 4px 12px; }}
    QLabel#badge[paused="true"] {{ border-color: {p.text_secondary}; color: {p.text_secondary}; }}
    QLabel#caption {{ color: {p.text_secondary}; }}
    QLabel#brain_title {{ font-size: 15px; font-weight: 600; }}
    QPushButton#pause {{ padding: 8px 12px; }}
    QPushButton {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.text_secondary};
        border-radius: 8px; padding: 8px 16px; }}
    QPushButton:hover {{ border-color: {p.primary}; }}
    QPushButton:focus {{ border: 2px solid {p.primary}; }}
    QPushButton#mini {{ padding: 4px 10px; border-radius: 6px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid {p.text_secondary}; background: {p.surface}; }}
    QCheckBox::indicator:checked {{ background: {p.primary}; border-color: {p.primary}; }}
    QToolButton#settings {{ border: 0; padding: 2px 8px; font-size: 18px; }}
    QToolButton#settings:hover {{ color: {p.primary}; }}
    QPushButton#care {{ background: {p.primary}; color: {p.on_primary};
        border-color: {p.primary}; }}
    """
