"""Salvar e carregar o cérebro (`cerebro.npz`), do jeito que o esquema (doc 05 §3) descreve.

- **Só o que foi aprendido vai para o disco:** pesos, máscaras de conexão, a média de
  recompensas r̄ e contadores. Potenciais e rastros não: ao abrir, o pet "acorda" com a rede
  zerada.
- **Versão:** o arquivo carrega `format_version`. Uma versão desconhecida (de um Pulso mais
  novo, por exemplo) é **recusada com aviso**, em vez de ser lida errado e estragar o cérebro.
- **Gravação atômica:** escreve num arquivo `.tmp` e só então o renomeia por cima do antigo
  (`os.replace`). Se faltar energia no meio, sobra o arquivo antigo inteiro, nunca um pela metade.
- **Nada de sensor:** nenhuma leitura de sensor passa por aqui (privacidade).
"""

import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from pulso.brain.engine import Engine
from pulso.brain.numpy_engine import NumpyEngine
from pulso.clock import Clock

log = logging.getLogger(__name__)

FORMAT_VERSION = 1
ENGINE_NAME = "numpy_lif_rstdp"
AUTOSAVE_INTERVAL_S = 300.0  # a cada 5 min

_META_KEYS = ("format_version", "engine", "groups", "seed", "saved_at")


class BrainFileError(ValueError):
    """O arquivo do cérebro não serve (versão desconhecida, outro motor, formato errado)."""


def save_brain(engine: Engine, path: Path, seed: int, saved_at: datetime | None = None) -> None:
    """Grava o cérebro de forma atômica. Cria a pasta se preciso."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (saved_at or datetime.now(UTC)).isoformat()
    arrays = {
        "format_version": np.array(FORMAT_VERSION),
        "engine": np.array(ENGINE_NAME),
        "groups": np.array(engine.groups),
        "seed": np.array(seed),
        "saved_at": np.array(stamp),
        **engine.state_dict(),
    }
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "wb") as f:  # arquivo aberto: o numpy não acrescenta ".npz" ao nome
            np.savez(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)  # se algo falhou antes do replace, não deixa lixo


def load_brain(engine: Engine, path: Path) -> int:
    """Carrega os pesos do arquivo para `engine`. Devolve a semente gravada.

    Levanta `BrainFileError` (e registra um aviso) se o arquivo não servir; nesse caso o `engine`
    não é alterado.
    """
    try:
        with np.load(Path(path), allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
    except Exception as exc:  # arquivo corrompido, truncado, não é npz...
        raise _refuse(f"não consegui ler o cérebro ({type(exc).__name__})") from exc

    missing = [k for k in _META_KEYS if k not in arrays]
    if missing:
        raise _refuse(f"arquivo sem os campos {missing}")
    version = int(arrays["format_version"])
    if version != FORMAT_VERSION:
        raise _refuse(
            f"versão {version} do arquivo é desconhecida (esta conhece a {FORMAT_VERSION})"
        )
    if str(arrays["engine"]) != ENGINE_NAME:
        raise _refuse(f"o arquivo é de outro motor ({str(arrays['engine'])!r})")
    if [str(g) for g in arrays["groups"]] != list(engine.groups):
        raise _refuse("os humores do arquivo não casam com os da rede")

    state = {k: v for k, v in arrays.items() if k not in _META_KEYS}
    try:
        engine.load_state_dict(state)
    except ValueError as exc:
        raise _refuse(f"pesos incompatíveis ({exc})") from exc
    return int(arrays["seed"])


def _refuse(reason: str) -> BrainFileError:
    log.warning("cérebro recusado: %s", reason)
    return BrainFileError(reason)


def load_or_create(path: Path, seed: int | None = None) -> tuple[NumpyEngine, int]:
    """Abre o cérebro salvo, ou cria um novo (primeiro uso) com semente sorteada.

    Se o arquivo existe mas não serve, a exceção sobe: quem chama decide (avisar o dono, guardar
    uma cópia). Nunca apagamos um arquivo ilegível por conta própria.
    """
    path = Path(path)
    if not path.exists():
        seed = secrets.randbits(31) if seed is None else seed
        return NumpyEngine(seed=seed), seed
    # A semente só é conhecida depois de ler o arquivo; o motor é reconstruído com ela.
    engine = NumpyEngine(seed=0)
    saved_seed = load_brain(engine, path)
    return engine, saved_seed


class AutoSaver:
    """Salva o cérebro a cada `interval_s`, e também sob demanda (ao pausar e ao sair)."""

    def __init__(
        self,
        engine: Engine,
        path: Path,
        seed: int,
        clock: Clock,
        interval_s: float = AUTOSAVE_INTERVAL_S,
    ) -> None:
        self._engine = engine
        self._path = Path(path)
        self._seed = seed
        self._clock = clock
        self._interval = interval_s
        self._last_save = clock.now()

    def tick(self) -> bool:
        """Chamado a cada volta do laço. Salva se já passou o intervalo; devolve se salvou."""
        if self._clock.now() - self._last_save < self._interval:
            return False
        self.flush()
        return True

    def flush(self) -> None:
        """Salva agora (ao pausar e ao sair). Um erro de disco vai para o log, sem derrubar."""
        try:
            save_brain(self._engine, self._path, self._seed)
            log.info("cérebro salvo")
        except OSError as exc:
            log.warning("falha ao salvar o cérebro (%s)", type(exc).__name__)
        # Mesmo se falhou, espera o intervalo antes de tentar de novo (não insiste a cada segundo).
        self._last_save = self._clock.now()
