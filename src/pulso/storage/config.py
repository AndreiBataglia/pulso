"""Preferências do dono (`config.toml`): o que a janela, a bandeja e os Ajustes deixam mudar.

Leitura com `tomllib` (biblioteca padrão). A escrita é feita à mão: são poucos valores (booleanos
e minutos inteiros), então não vale uma dependência só para isso. Valor ausente, de tipo errado ou
fora do intervalo volta ao padrão, com aviso no log: um arquivo editado errado nunca impede o
Pulso de abrir. "Iniciar com o Windows" não fica aqui: o registro do Windows é a fonte da
verdade (`storage/autostart.py`).
"""

import logging
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from pulso.habits.kinds import HabitConfig

log = logging.getLogger(__name__)

CONFIG_FILE = "config.toml"


@dataclass(frozen=True)
class Settings:
    always_on_top: bool = True  # a janela fica sobre as outras (o Pulso precisa ser visto)
    water_enabled: bool = True  # lembrete de água ligado
    focus_min: int = 50  # tempos do pomodoro e da água, em minutos
    break_min: int = 10
    long_break_min: int = 20
    water_interval_min: int = 60
    water_ml: int = 250  # quanto cada "Bebi" soma (copo, garrafa...), em ml
    away_min: int = 5  # parado por mais que isto = ausente: o foco para no último gesto
    mode: str = "profissional"  # "profissional" (conta foco e chama para a pausa) ou "casual"


# Seção do TOML de cada campo.
_SECTIONS = {
    "always_on_top": "window",
    "water_enabled": "habits",
    "focus_min": "habits",
    "break_min": "habits",
    "long_break_min": "habits",
    "water_interval_min": "habits",
    "water_ml": "habits",
    "away_min": "habits",
    "mode": "habits",
}
# Intervalo aceito (mínimo, máximo) dos tempos, em minutos.
RANGES = {
    "focus_min": (5, 180),
    "break_min": (1, 60),
    "long_break_min": (1, 120),
    "water_interval_min": (10, 240),
    "water_ml": (50, 2000),
    "away_min": (1, 30),
}
# Campos de texto: só estes valores valem.
CHOICES = {"mode": ("profissional", "casual")}


def _valid(name: str, value, default) -> bool:
    if isinstance(default, str):
        return isinstance(value, str) and value in CHOICES[name]
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    low, high = RANGES[name]
    return low <= value <= high


def habit_config(settings: Settings) -> HabitConfig:
    """Os tempos dos hábitos com o que o dono escolheu (o resto fica no padrão)."""
    return HabitConfig(
        focus_min=settings.focus_min,
        break_min=settings.break_min,
        long_break_min=settings.long_break_min,
        water_interval_min=settings.water_interval_min,
        water_ml=settings.water_ml,
        away_idle_s=settings.away_min * 60.0,
    )


def load_settings(path: Path) -> Settings:
    """Lê as preferências; qualquer problema vira o valor padrão."""
    defaults = Settings()
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return defaults
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("config.toml ilegível (%s); usando os padrões", type(exc).__name__)
        return defaults
    values = {}
    for field in fields(Settings):
        section = data.get(_SECTIONS[field.name], {})
        value = section.get(field.name) if isinstance(section, dict) else None
        if _valid(field.name, value, getattr(defaults, field.name)):
            values[field.name] = value
        elif value is not None:
            log.warning("config.toml: %s inválido; usando o padrão", field.name)
    return Settings(**{**defaults.__dict__, **values})


def save_settings(path: Path, settings: Settings) -> None:
    """Grava de forma atômica (arquivo temporário e `os.replace`), criando a pasta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section in dict.fromkeys(_SECTIONS.values()):
        lines.append(f"[{section}]")
        for field in fields(Settings):
            if _SECTIONS[field.name] == section:
                value = getattr(settings, field.name)
                text = f'"{value}"' if isinstance(value, str) else str(value).lower()
                lines.append(f"{field.name} = {text}")  # True → true; 50 → 50; "casual" → "casual"
        lines.append("")
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text("\n".join(lines), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
