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
from pulso.habits.coach import HabitCoach
from pulso.sensors.base import Sensor
from pulso.storage.autostart import Autostart
from pulso.storage.brain_store import AutoSaver, BrainFileError, load_or_create
from pulso.storage.config import CONFIG_FILE, load_settings, save_settings
from pulso.storage.db import HabitStore, open_db
from pulso.storage.paths import DB_FILE, brain_path, data_dir
from pulso.ui.main_window import MainWindow
from pulso.ui.theme import DARK, LIGHT, stylesheet
from pulso.ui.tray import Tray, pulso_icon

log = logging.getLogger(__name__)


def build_controller(
    sensor: Sensor,
    clock: Clock,
    path: Path,
    warn=lambda text: None,
    db: Path | str | None = None,
) -> tuple[PetController, bool]:
    """Abre o cérebro salvo (ou cria um novo) e monta o controlador.

    `db` é o arquivo do banco de hábitos (padrão: `pulso.db` ao lado do cérebro).

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
    habits = HabitCoach(clock, HabitStore(open_db(db if db is not None else path.parent / DB_FILE)))
    controller = PetController(
        sensor,
        clock,
        engine,
        decoder,
        RewardRules(clock),
        AutoSaver(engine, path, seed, clock),
        habits,
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
    app.setWindowIcon(pulso_icon())
    # O X da janela esconde o pet na bandeja; quem encerra de verdade é "Sair do Pulso".
    app.setQuitOnLastWindowClosed(False)
    config = data_dir() / CONFIG_FILE
    window = MainWindow(
        controller,
        clock,
        first_run=first_run,
        palette=DARK if dark else LIGHT,
        tray=Tray(),
        settings=load_settings(config),
        save_settings=lambda settings: save_settings(config, settings),
        autostart=Autostart(),
    )
    # Fim de sessão do Windows (desligar/sair): o X não pode segurar o encerramento.
    app.commitDataRequest.connect(window.prepare_to_quit)
    window.show()
    return app.exec()
