"""Confirmação de "Remover o Pulso": mostra o que será apagado, oferece o backup e só libera o botão
quando o dono digita REMOVER. Não apaga nada: quem apaga é a janela principal, se ele aceitar."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pulso.storage import uninstall


class RemoveDialog(QDialog):
    def __init__(self, data_dir: Path, lines: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remover o Pulso")
        self._data_dir = data_dir
        self.backup_path: Path | None = None
        intro = QLabel(
            "Isto apaga o Pulso deste computador, <b>sem volta</b>: o que a rede aprendeu, "
            "o histórico de hábitos, os ajustes e o início com o Windows."
        )
        intro.setWordWrap(True)
        items = QLabel("\n".join(lines))
        items.setWordWrap(True)
        items.setObjectName("caption")
        self.backup_button = QPushButton("Guardar um backup antes…")
        self.backup_button.clicked.connect(self._choose_backup)
        self.backup_label = QLabel("")
        self.backup_label.setObjectName("caption")
        self.backup_label.setWordWrap(True)
        ask = QLabel(f"Para confirmar, digite {uninstall.CONFIRMATION}:")
        self.confirm = QLineEdit()
        self.confirm.textChanged.connect(self._check)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Remover tudo")
        self.ok_button.setEnabled(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        for widget in (intro, items, self.backup_button, self.backup_label, ask, self.confirm):
            layout.addWidget(widget)
        layout.addWidget(self.buttons)

    def _check(self, text: str) -> None:
        self.ok_button.setEnabled(text.strip() == uninstall.CONFIRMATION)

    def _choose_backup(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Onde guardar o backup?")
        if folder:
            self.make_backup(Path(folder))

    def make_backup(self, folder: Path) -> None:
        try:
            self.backup_path = uninstall.backup(self._data_dir, folder)
            self.backup_label.setText(f"Backup guardado em {self.backup_path}")
        except OSError as exc:
            self.backup_path = None
            self.backup_label.setText(f"Não consegui guardar o backup ({type(exc).__name__}).")
