"""Atalho do Pulso no Menu Iniciar, para abrir o app de novo depois de "Sair do Pulso".

Um `.lnk` é um arquivo do Windows (não um texto): criá-lo pede o objeto COM `WScript.Shell`. Chamo o
PowerShell, que já o tem, e passo os valores por variáveis de ambiente (sem se preocupar com aspas).
"""

import os
import subprocess
from pathlib import Path

from pulso.storage.autostart import windowless_python

SHORTCUT_NAME = "Pulso.lnk"

_SCRIPT = (
    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PULSO_LNK);"
    "$s.TargetPath = $env:PULSO_TARGET; $s.Arguments = $env:PULSO_ARGS;"
    "$s.WorkingDirectory = $env:PULSO_WORKDIR; $s.Description = 'Pulso, o companheiro de desktop';"
    "if ($env:PULSO_ICON) { $s.IconLocation = $env:PULSO_ICON };"
    "$s.Save()"
)


def start_menu_shortcut() -> Path:
    """Onde fica o atalho: a pasta Programas do Menu Iniciar do usuário (sem administrador)."""
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / SHORTCUT_NAME


def create_shortcut(
    lnk: Path, target: Path | None = None, args: str = "-m pulso", icon: Path | None = None
) -> Path:
    """Cria (ou refaz) o atalho `lnk`. Levanta `OSError` se o PowerShell falhar."""
    target = target or windowless_python()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PULSO_LNK": str(lnk),
        "PULSO_TARGET": str(target),
        "PULSO_ARGS": args,
        "PULSO_WORKDIR": str(Path.home()),
        "PULSO_ICON": str(icon) if icon else "",
    }
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not lnk.exists():
        raise OSError(f"não consegui criar o atalho: {result.stderr.strip()}")
    return lnk
