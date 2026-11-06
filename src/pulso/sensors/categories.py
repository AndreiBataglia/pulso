"""Tabela processo → categoria. A categoria vem só do nome do executável."""

from collections.abc import Mapping

from pulso.sensors.base import UNKNOWN_CATEGORY

# Categorias: codigo, navegador, video, chat, escritorio, jogo, outro.
DEFAULT_CATEGORIES: dict[str, str] = {
    # código
    "code.exe": "codigo",
    "pycharm64.exe": "codigo",
    "devenv.exe": "codigo",
    "windowsterminal.exe": "codigo",
    "powershell.exe": "codigo",
    "cmd.exe": "codigo",
    # navegador
    "chrome.exe": "navegador",
    "msedge.exe": "navegador",
    "firefox.exe": "navegador",
    "brave.exe": "navegador",
    "opera.exe": "navegador",
    # vídeo
    "vlc.exe": "video",
    "spotify.exe": "video",
    "netflix.exe": "video",
    "mpc-hc64.exe": "video",
    # chat
    "whatsapp.exe": "chat",
    "telegram.exe": "chat",
    "discord.exe": "chat",
    "slack.exe": "chat",
    "teams.exe": "chat",
    "ms-teams.exe": "chat",
    # escritório
    "winword.exe": "escritorio",
    "excel.exe": "escritorio",
    "powerpnt.exe": "escritorio",
    "outlook.exe": "escritorio",
    "onenote.exe": "escritorio",
    "notepad.exe": "escritorio",
    # jogo
    "steam.exe": "jogo",
    "epicgameslauncher.exe": "jogo",
}


def categorize(process_name: str | None, extra: Mapping[str, str] | None = None) -> str:
    """Devolve a categoria do processo; desconhecido (ou vazio) cai em "outro", sem erro.

    `extra` é a tabela do dono (config.toml) e sobrepõe a embutida. A busca ignora maiúsculas.
    """
    if not process_name:
        return UNKNOWN_CATEGORY
    name = process_name.strip().lower()
    if extra:
        merged = {k.lower(): v for k, v in extra.items()}
        if name in merged:
            return merged[name]
    return DEFAULT_CATEGORIES.get(name, UNKNOWN_CATEGORY)
