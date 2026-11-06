"""Tela de Ajustes: os tempos do pomodoro e da água, e se a rede aprende também com o que vê no PC.

Só monta e devolve um `Settings` novo (`settings()`); quem grava e aplica é a janela principal.
"""

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pulso.storage.config import RANGES, Settings

_LABELS = {
    "focus_min": "Foco",
    "break_min": "Descanso curto",
    "long_break_min": "Descanso longo (a cada 4 focos)",
    "water_interval_min": "Lembrar de beber água a cada",
}


class SettingsDialog(QDialog):
    def __init__(self, current: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustes do Pulso")
        self._current = current
        form = QFormLayout()
        self.spins: dict[str, QSpinBox] = {}
        for name, label in _LABELS.items():
            spin = QSpinBox()
            spin.setRange(*RANGES[name])
            spin.setSuffix(" min")
            spin.setValue(getattr(current, name))
            self.spins[name] = spin
            form.addRow(label, spin)
        self.auto_rules = QCheckBox("Aprender também com o que vejo no PC")
        self.auto_rules.setChecked(current.auto_rules)
        self.auto_rules.setToolTip(
            "Regras por processo e ócio (palpites sobre o seu humor). Desligado, o Pulso aprende "
            "só com carinho, bronca e os seus hábitos."
        )
        note = QLabel(
            "Os tempos novos valem já para a próxima fase do pomodoro e para o próximo lembrete."
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
        layout.addWidget(self.auto_rules)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def settings(self) -> Settings:
        """As preferências com o que está na tela (o resto fica como estava)."""
        values = {name: spin.value() for name, spin in self.spins.items()}
        return replace(self._current, auto_rules=self.auto_rules.isChecked(), **values)
