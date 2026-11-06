"""Iniciar com o Windows: um valor na chave `Run` do usuário (`HKCU`), sem administrador.

Escolhi o registro em vez de um atalho na pasta Inicializar: é só gravar e apagar um valor com
`winreg` (biblioteca padrão), sem criar `.lnk` (que pede COM ou PowerShell). O Windows lê a
chave no login e roda o comando. Usa `pythonw.exe` (sem janela de console preta) com `-m pulso`.
"""

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Pulso"


def windowless_python() -> Path:
    """O `pythonw.exe` ao lado do Python de agora (sem console preto); se não houver, o próprio."""
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")
    return windowless if windowless.exists() else python


MINIMIZED_ARG = "--minimizado"


def default_command() -> str:
    """O comando que o Windows roda no login: o mesmo Python de agora, sem console.

    Com `--minimizado` o Pulso abre só na bandeja, sem a janela na cara do dono.
    """
    return f'"{windowless_python()}" -m pulso {MINIMIZED_ARG}'


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

    def migrate(self) -> bool:
        """Reescreve a chave antiga (sem `--minimizado`) para abrir só na bandeja.

        Só mexe se o dono já tinha ligado a opção; nunca liga sozinha. Devolve True se reescreveu.
        """
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                current = winreg.QueryValueEx(key, VALUE_NAME)[0]
            if MINIMIZED_ARG in str(current):
                return False
            self.set_enabled(True)
            return True
        except (OSError, ImportError):  # desligado, sem permissão ou fora do Windows
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
