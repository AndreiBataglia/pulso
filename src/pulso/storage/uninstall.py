"""Remover o Pulso: apaga tudo que é dele no computador (o "desinstalador").

O que é apagado:
- os arquivos **conhecidos** da pasta de dados (`%LOCALAPPDATA%\\Pulso`): cérebro, cérebros
  recusados, banco, config e ícone;
- a chave "Iniciar com o Windows";
- o atalho do Menu Iniciar.

Cuidados (não tem volta, então o código é conservador):
- **nunca** usa `rmtree`: apaga só os nomes que o Pulso cria. Se a pasta tiver outra coisa (um
  backup seu, por exemplo), ela fica, e o relatório avisa;
- recusa pastas perigosas (raiz do disco, pasta pessoal, atalho/junção) e qualquer pasta que não se
  chame "Pulso" nem tenha os arquivos do Pulso dentro;
- o backup (`backup`) é um `.zip` com os mesmos arquivos, feito antes, se o dono quiser.

O programa em si (o pacote Python) sai com `pip uninstall pulso`; o Pulso não se apaga sozinho.
"""

import fnmatch
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from pulso.storage.paths import BRAIN_FILE, DB_FILE

# Nomes que o Pulso cria na pasta de dados (padrões do `fnmatch`).
KNOWN_FILES = (
    BRAIN_FILE,
    "cerebro.recusado-*.npz",
    "cerebro.npz.tmp",
    DB_FILE,
    DB_FILE + "-wal",
    DB_FILE + "-shm",
    DB_FILE + "-journal",
    "config.toml",
    "pulso.ico",
)
MARKERS = (BRAIN_FILE, DB_FILE)  # quem tem um destes dentro é, com quase certeza, a pasta do Pulso
CONFIRMATION = "REMOVER"
PIP_HINT = "pip uninstall pulso"


class AutostartLike(Protocol):
    def enabled(self) -> bool: ...
    def set_enabled(self, on: bool) -> None: ...


class UnsafeFolderError(ValueError):
    """A pasta não parece ser a do Pulso: nada é apagado."""


@dataclass
class RemovalReport:
    removed: list[str] = field(default_factory=list)  # o que foi apagado
    failed: list[tuple[str, str]] = field(default_factory=list)  # (o quê, por quê)
    folder_removed: bool = False
    folder_kept_reason: str | None = None  # pasta mantida porque sobrou algo que não é do Pulso

    @property
    def ok(self) -> bool:
        return not self.failed


def check_folder(data_dir: Path) -> Path:
    """Confere que `data_dir` é mesmo a pasta do Pulso. Devolve o caminho resolvido ou levanta
    `UnsafeFolderError`."""
    path = Path(data_dir)
    if path.is_symlink():
        raise UnsafeFolderError(
            "a pasta é um atalho/junção; não apago o que não é pasta de verdade"
        )
    resolved = path.resolve()
    if resolved == resolved.anchor or len(resolved.parts) < 3:
        raise UnsafeFolderError("pasta perto demais da raiz do disco")
    if resolved == Path.home().resolve():
        raise UnsafeFolderError("esta é a sua pasta pessoal")
    has_marker = resolved.is_dir() and any((resolved / m).exists() for m in MARKERS)
    if resolved.name.lower() != "pulso" and not has_marker:
        raise UnsafeFolderError("a pasta não se chama Pulso nem tem o cérebro ou o banco do Pulso")
    return resolved


def find_files(data_dir: Path) -> list[Path]:
    """Os arquivos do Pulso que existem na pasta (só os de nomes conhecidos)."""
    folder = Path(data_dir)
    if not folder.is_dir():
        return []
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and any(fnmatch.fnmatch(p.name, pattern) for pattern in KNOWN_FILES)
    )


def describe(data_dir: Path, autostart: AutostartLike | None, shortcut: Path | None) -> list[str]:
    """O que seria apagado, em frases, para mostrar ao dono antes de confirmar."""
    lines = [f"Pasta de dados: {data_dir}"]
    lines += [f"  • {p.name}" for p in find_files(data_dir)]
    if autostart is not None and autostart.enabled():
        lines.append('"Iniciar com o Windows" (chave do registro)')
    if shortcut is not None and shortcut.exists():
        lines.append(f"Atalho do Menu Iniciar: {shortcut}")
    return lines


def backup(data_dir: Path, dest_dir: Path, now: datetime | None = None) -> Path:
    """Guarda uma cópia dos arquivos do Pulso num `.zip` dentro de `dest_dir`. Não apaga nada."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target = dest_dir / f"pulso-backup-{stamp}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in find_files(data_dir):
            archive.write(path, arcname=path.name)
    return target


def remove_all(
    data_dir: Path, autostart: AutostartLike | None = None, shortcut: Path | None = None
) -> RemovalReport:
    """Apaga tudo do Pulso. Levanta `UnsafeFolderError` (sem apagar nada) se a pasta for suspeita.

    Um item que falha (arquivo em uso, por exemplo) não interrompe os outros: vai para `failed`.
    """
    folder = check_folder(data_dir)
    report = RemovalReport()

    for path in find_files(folder):
        try:
            path.unlink()
            report.removed.append(path.name)
        except OSError as exc:
            report.failed.append((path.name, type(exc).__name__))

    if autostart is not None:
        try:
            if autostart.enabled():
                autostart.set_enabled(False)
                report.removed.append("Iniciar com o Windows")
        except OSError as exc:
            report.failed.append(("Iniciar com o Windows", type(exc).__name__))

    if shortcut is not None and shortcut.name.lower() == "pulso.lnk" and shortcut.exists():
        try:
            shortcut.unlink()
            report.removed.append("atalho do Menu Iniciar")
        except OSError as exc:
            report.failed.append(("atalho do Menu Iniciar", type(exc).__name__))

    if folder.is_dir():
        try:
            folder.rmdir()  # só funciona se estiver vazia: nunca apaga o que não é do Pulso
            report.folder_removed = True
        except OSError:
            left = [p.name for p in folder.iterdir()] if folder.is_dir() else []
            if left:
                report.folder_kept_reason = "sobraram arquivos que não são do Pulso: " + ", ".join(
                    left
                )
    return report


def summary(report: RemovalReport) -> str:
    """Texto final para o dono."""
    lines = [f"Apagado: {', '.join(report.removed) or 'nada (já estava limpo)'}."]
    if report.folder_removed:
        lines.append("A pasta de dados foi removida.")
    if report.folder_kept_reason:
        lines.append(f"A pasta foi mantida: {report.folder_kept_reason}.")
    for what, why in report.failed:
        lines.append(f"Não consegui apagar {what} ({why}).")
    lines.append(f"Para tirar o programa do Python, rode: {PIP_HINT}")
    return "\n".join(lines)
