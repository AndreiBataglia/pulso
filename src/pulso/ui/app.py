"""Monta o app: cérebro (novo ou salvo), controlador, janela e tema. É o que `pulso` abre."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import Clock, SystemClock
from pulso.controller import PetController
from pulso.sensors.base import Sensor
from pulso.storage.brain_store import AutoSaver, BrainFileError, load_or_create
from pulso.storage.paths import brain_path
from pulso.ui.main_window import MainWindow
from pulso.ui.theme import DARK, LIGHT, stylesheet

log = logging.getLogger(__name__)


def build_controller(
    sensor: Sensor, clock: Clock, path: Path, warn=lambda text: None
) -> tuple[PetController, bool]:
    """Abre o cérebro salvo (ou cria um novo) e monta o controlador.

    Devolve `(controlador, primeiro_uso)`.

    Se o arquivo existe mas não serve (`BrainFileError`), ele **não é apagado**: é renomeado para
    `cerebro.recusado-<data>.npz` (para o dono ou uma versão futura poderem recuperá-lo), `warn`
    avisa o dono e começa um cérebro novo.
    """
    first_run = not path.exists()
    new_brain = first_run
    try:
        engine, seed = load_or_create(path)
    except BrainFileError as exc:
        kept = path.with_name(f"{path.stem}.recusado-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
        path.rename(kept)
        warn(
            f"Não consegui abrir o cérebro salvo ({exc}).\n"
            f"Guardei o arquivo como {kept.name} e comecei um cérebro novo."
        )
        engine, seed = load_or_create(path)
        first_run = False  # o dono já conhece o pet; só o cérebro recomeçou
        new_brain = True
    decoder = MoodDecoder(engine.groups)
    controller = PetController(
        sensor, clock, engine, decoder, RewardRules(clock), AutoSaver(engine, path, seed, clock)
    )
    if new_brain:
        controller.shutdown()  # grava já: o arquivo marca que o primeiro uso aconteceu
    return controller, first_run


def run(fake_sensors: bool = False) -> int:
    clock = SystemClock()
    if fake_sensors:
        from pulso.sensors.fake import ScriptedSensor, demo_scenario

        sensor: Sensor = ScriptedSensor(demo_scenario())
    else:
        from pulso.sensors.windows import WindowsSensor

        sensor = WindowsSensor(clock)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Pulso")
    dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    app.setStyleSheet(stylesheet(DARK if dark else LIGHT))

    def warn(text: str) -> None:
        QMessageBox.warning(None, "Pulso", text)

    controller, first_run = build_controller(sensor, clock, brain_path(), warn)
    window = MainWindow(controller, clock, first_run=first_run, palette=DARK if dark else LIGHT)
    window.show()
    return app.exec()
