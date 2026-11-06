"""Preferências do dono (`config.toml`): só o que a janela e a bandeja deixam ligar e desligar.

Leitura com `tomllib` (biblioteca padrão). A escrita é feita à mão: são poucos booleanos, então não
vale uma dependência só para isso. Valor ausente ou de tipo errado volta ao padrão, com aviso no
log: um arquivo editado errado nunca impede o Pulso de abrir. "Iniciar com o Windows" não fica
aqui: o registro do Windows é a fonte da verdade (`storage/autostart.py`).
"""

import logging
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_FILE = "config.toml"


@dataclass(frozen=True)
class Settings:
    always_on_top: bool = True  # a janela fica sobre as outras (o pet precisa ser visto)
    water_enabled: bool = True  # lembrete de água ligado


# Seção do TOML de cada campo.
_SECTIONS = {"always_on_top": "window", "water_enabled": "habits"}


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
        if isinstance(value, bool):
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
                lines.append(f"{field.name} = {str(getattr(settings, field.name)).lower()}")
        lines.append("")
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text("\n".join(lines), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
