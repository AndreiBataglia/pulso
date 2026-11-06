"""Testes de interface rodam sem tela (`offscreen`) e nunca tocam nos dados reais do dono."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    # Sem isto, janelas esquecidas (com QTimer) derrubam o processo no encerramento do Qt
    # (código 0xC0000409 no Windows), mesmo com todos os testes verdes.
    # Só as janelas do app: o pyqtgraph cria `QMenu`s de topo que pertencem a ele, e apagá-los daqui
    # derruba o Qt (Fatal Python error: Aborted) na hora do `DeferredDelete`.
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            widget.close()
            widget.deleteLater()
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
