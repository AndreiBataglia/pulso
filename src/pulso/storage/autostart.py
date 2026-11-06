"""Iniciar com o Windows: um valor na chave `Run` do usuário (`HKCU`), sem administrador.

Escolhi o registro em vez de um atalho na pasta Inicializar: é só gravar e apagar um valor com
`winreg` (biblioteca padrão), sem criar `.lnk` (que pede COM ou PowerShell). O Windows lê a
chave no login e roda o comando. Usa `pythonw.exe` (sem janela de console preta) com `-m pulso`.
"""

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Pulso"


def default_command() -> str:
    """O comando que o Windows roda no login: o mesmo Python de agora, sem console."""
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")
    return f'"{windowless if windowless.exists() else python}" -m pulso'


class Autostart:
    def __init__(self, key_path: str = RUN_KEY, command: str | None = None) -> None:
        self._key_path = key_path
        self._command = command

    def enabled(self) -> bool:
        """O Pulso está na lista de programas que iniciam com o Windows?"""
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                winreg.QueryValueEx(key, VALUE_NAME)
            return True
        except (OSError, ImportError):  # sem chave/valor, ou fora do Windows
            return False

    def set_enabled(self, on: bool) -> None:
        """Liga ou desliga. Levanta `OSError` se o Windows recusar (a janela avisa o dono)."""
        import winreg

        if on:
            command = self._command or default_command()
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, self._key_path, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, self._key_path, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass  # já estava desligado
