"""A bandeja do Windows (T05 e T06): ícone sempre visível, menu e avisos (`QSystemTrayIcon`).

O ícone fica na bandeja desde que o Pulso abre: é por ele que se reabre a janela depois de "fechar".
As ações do menu são montadas pela janela (`add_action`); aqui só mora a mecânica do Qt. Os avisos
("hora da água", "hora do descanso", "hora de voltar") saem por `notify`. Sem som nosso: o Pulso é
discreto (Design Brief §1); o que o Windows toca é escolha dele.
"""

from collections.abc import Callable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from pulso.ui.theme import FACE_BACKGROUND, MOOD_COLORS

TITLE = "Pulso"
SHOW_MS = 8000


def pulso_icon() -> QIcon:
    """O rostinho do Pulso (fundo escuro, dois olhos e um sorriso), desenhado em código."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(FACE_BACKGROUND))
    p.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), 14, 14)
    p.setBrush(QColor(MOOD_COLORS["contente"]))
    for x in (20, 44):
        p.drawEllipse(QRectF(x - 5, 20, 10, 14))
    p.setPen(QColor(MOOD_COLORS["contente"]))
    p.drawArc(QRectF(22, 36, 20, 12), 200 * 16, 140 * 16)
    p.end()
    return QIcon(pixmap)


class Tray:
    """Ícone da bandeja com menu e avisos (sem bandeja no sistema, avisar não faz nada)."""

    def __init__(self) -> None:
        self.menu = QMenu()
        self._disposed = False
        self._icon = QSystemTrayIcon(pulso_icon())
        self._icon.setToolTip(TITLE)
        self._icon.setContextMenu(self.menu)

    @property
    def available(self) -> bool:
        """O Windows tem bandeja agora? (Logo no login ela pode ainda não existir.)"""
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self._icon.show()

    def add_action(
        self, text: str, callback: Callable, checkable: bool = False, checked: bool = False,
        menu: QMenu | None = None,
    ) -> QAction:  # fmt: skip
        """Põe um item no menu (ou num submenu). Itens marcáveis chamam `callback(marcado)`."""
        action = (menu or self.menu).addAction(text)
        if checkable:
            action.setCheckable(True)
            action.setChecked(checked)
            action.triggered.connect(callback)
        else:
            action.triggered.connect(lambda _checked=False: callback())
        return action

    def add_submenu(self, title: str) -> QMenu:
        return self.menu.addMenu(title)

    def notify(self, text: str) -> None:
        if self.available:
            self._icon.showMessage(TITLE, text, QSystemTrayIcon.MessageIcon.NoIcon, SHOW_MS)

    def on_click(self, callback: Callable[[], None]) -> None:
        """Clicar na notificação chama `callback` (abrir a janela do pet)."""
        self._icon.messageClicked.connect(callback)

    def on_open(self, callback: Callable[[], None]) -> None:
        """Clicar (ou clicar duas vezes) no ícone chama `callback` (abrir a janela do pet)."""
        reasons = (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        )
        self._icon.activated.connect(lambda reason: callback() if reason in reasons else None)

    def dispose(self) -> None:
        """Tira o ícone da bandeja e apaga o menu (ao sair de vez)."""
        if self._disposed:
            return
        self._disposed = True
        self._icon.hide()
        self.menu.deleteLater()
