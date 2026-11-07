"""Tela de Ajustes: tempos do foco e da água, tolerância de ausência, modo, e se a rede aprende
também com o que vê no PC.

Só monta e devolve um `Settings` novo (`settings()`); quem grava e aplica é a janela principal.
"""

from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pulso.habits.focus_cycle import Mode
from pulso.storage.config import RANGES, Settings

_LABELS = {
    "focus_min": "Foco",
    "break_min": "Descanso curto",
    "long_break_min": "Descanso longo (a cada 4 focos)",
    "water_interval_min": "Lembrar de beber água a cada",
    "water_ml": 'Água de cada "Bebi" (seu copo ou garrafa)',
    "away_min": "Parado por mais de (conta como ausente)",
}
_MODES = {Mode.PROFESSIONAL: "Profissional", Mode.CASUAL: "Casual (só a água)"}


class SettingsDialog(QDialog):
    def __init__(self, current: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustes do Pulso")
        self._current = current
        form = QFormLayout()
        self.mode = QComboBox()
        for mode, text in _MODES.items():
            self.mode.addItem(text, mode.value)
        self.mode.setCurrentIndex(self.mode.findData(current.mode))
        form.addRow("Modo", self.mode)
        self.spins: dict[str, QSpinBox] = {}
        for name, label in _LABELS.items():
            spin = QSpinBox()
            spin.setRange(*RANGES[name])
            spin.setSuffix(" ml" if name == "water_ml" else " min")
            if name == "water_ml":
                spin.setSingleStep(50)
            spin.setValue(getattr(current, name))
            self.spins[name] = spin
            form.addRow(label, spin)
        note = QLabel(
            "Os tempos novos valem já para o próximo foco, o próximo descanso e o próximo lembrete."
        )
        note.setObjectName("caption")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def settings(self) -> Settings:
        """As preferências com o que está na tela (o resto fica como estava)."""
        values = {name: spin.value() for name, spin in self.spins.items()}
        return replace(
            self._current,
            mode=self.mode.currentData(),
            **values,
        )
