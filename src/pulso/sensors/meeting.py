"""Sensor de reunião: "o microfone está em uso por algum programa?" (nível B, só metadado).

O Windows registra, por programa, quando ele começou e parou de usar o microfone
(`CapabilityAccessManager\\ConsentStore\\microphone`). Aqui só se pergunta **se** algum
está em uso agora: o Pulso **não captura som**, **não grava o nome do programa** (a resposta é
um sim/não) e **nunca** usa o microfone ou a câmera como sensor de presença. Cobre Teams, Meet,
Zoom e afins, no app ou no navegador, sem ler título de janela nem endereço.

Limite conhecido: se um programa travar com o microfone aberto, o registro pode ficar "em uso" até
ele fechar; o pior efeito é o foco ficar pausado, e o dono vê "Em reunião" e pode trocar de modo.
"""

import sys
from typing import Protocol

_CONSENT_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
)


class MeetingSensor(Protocol):
    def in_meeting(self) -> bool: ...


class FakeMeetingSensor:
    """Para os testes: o roteiro diz se há reunião a cada chamada (repete o último valor)."""

    def __init__(self, script: list[bool] | None = None) -> None:
        self._script = list(script or [False])
        self.calls = 0

    def in_meeting(self) -> bool:
        value = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        return value


class WindowsMeetingSensor:
    """Lê o registro do Windows (só leitura). Qualquer falha vale "sem reunião"."""

    def __init__(self, key_path: str = _CONSENT_KEY) -> None:
        self._key_path = key_path

    def in_meeting(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as root:
                if self._any_in_use(winreg, root):  # apps da loja
                    return True
                with winreg.OpenKey(root, "NonPackaged") as classic:  # programas comuns (.exe)
                    return self._any_in_use(winreg, classic)
        except OSError:
            return False

    @staticmethod
    def _any_in_use(winreg, key) -> bool:
        """Algum subitem com início registrado e sem parada (`LastUsedTimeStop` = 0)?"""
        count = winreg.QueryInfoKey(key)[0]
        for index in range(count):
            try:
                with winreg.OpenKey(key, winreg.EnumKey(key, index)) as app:
                    start = winreg.QueryValueEx(app, "LastUsedTimeStart")[0]
                    stop = winreg.QueryValueEx(app, "LastUsedTimeStop")[0]
            except OSError:  # item sem esses valores (ex.: a pasta NonPackaged): pula
                continue
            if start and not stop:
                return True
        return False
