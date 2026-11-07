"""O banco de hábitos (`pulso.db`, SQLite): só eventos de hábito, nunca dado de sensor.

- **Migrações:** a versão do esquema fica na tabela `meta` (`schema_version`). Os scripts de
  `MIGRATIONS` rodam em ordem, cada um numa transação, só os que faltam. Um banco de versão
  **mais nova** que a conhecida é recusado (um Pulso antigo não deve mexer no que não entende).
- **Pendência:** não é guardada; é calculada dos eventos (recusas e omissões desde o último "fiz"),
  então sobrevive a fechar o app sem nenhuma coluna a mais.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from pulso.habits import kinds

log = logging.getLogger(__name__)

# A v1 guarda a lista de tipos de quando nasceu (uma migração antiga nunca muda com o tempo).
_V1_KIND_LIST = ", ".join(f"'{k}'" for k in kinds.ALL_KINDS if k not in kinds.V3_KINDS)
_KIND_LIST = ", ".join(f"'{k}'" for k in kinds.ALL_KINDS)
_CATEGORY_LIST = ", ".join(f"'{c}'" for c in kinds.CATEGORIES)

MIGRATIONS = (
    # v1
    f"""
    CREATE TABLE habit_event (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        ts    TEXT NOT NULL,
        kind  TEXT NOT NULL CHECK (kind IN ({_V1_KIND_LIST})),
        value INTEGER
    );
    CREATE INDEX idx_habit_event_ts ON habit_event (ts);
    """,
    # v2: placar dos jogos (jokenpô e par ou ímpar), do ponto de vista do Pulso
    """
    CREATE TABLE game_result (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        ts     TEXT NOT NULL,
        game   TEXT NOT NULL CHECK (game IN ('rps', 'evenodd')),
        result TEXT NOT NULL CHECK (result IN ('won', 'lost', 'draw'))
    );
    CREATE INDEX idx_game_result_ts ON game_result (ts);
    """,
    # v3: o ciclo de foco por presença. O SQLite não altera um CHECK: refaz a tabela e copia tudo.
    # Novos: tipos `away_need`/`away_focus`, `category` (a resposta de "o que foi?") e o resumo da
    # pausa em segundos (planejado, feito, excesso). Nunca o sinal do sensor.
    f"""
    CREATE TABLE habit_event_v3 (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        TEXT NOT NULL,
        kind      TEXT NOT NULL CHECK (kind IN ({_KIND_LIST})),
        value     INTEGER,
        category  TEXT CHECK (category IS NULL OR category IN ({_CATEGORY_LIST})),
        planned_s INTEGER,
        actual_s  INTEGER,
        excess_s  INTEGER
    );
    INSERT INTO habit_event_v3 (id, ts, kind, value) SELECT id, ts, kind, value FROM habit_event;
    DROP TABLE habit_event;
    ALTER TABLE habit_event_v3 RENAME TO habit_event;
    CREATE INDEX idx_habit_event_ts ON habit_event (ts);
    """,
)
SCHEMA_VERSION = len(MIGRATIONS)

# Cada hábito tem o seu "fiz" (que zera a pendência) e as suas recusas/omissões (que a somam).
PENDING_GROUPS = {
    "water": (kinds.WATER_DRUNK, kinds.WATER_DECLINED, kinds.WATER_IGNORED),
    "break": (kinds.BREAK_DONE, kinds.BREAK_DECLINED, kinds.BREAK_IGNORED),
}


class DbVersionError(ValueError):
    """O banco é de uma versão mais nova que esta."""


def open_db(path: Path | str) -> sqlite3.Connection:
    """Abre (criando a pasta e o arquivo) e migra para a versão atual. `":memory:"` para testes."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)  # transações controladas aqui
    try:
        _migrate(conn)
    except Exception:
        conn.close()
        raise
    return conn


def _version(conn: sqlite3.Connection) -> int:
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    return int(row[0]) if row else 0


def _migrate(conn: sqlite3.Connection) -> None:
    version = _version(conn)
    if version > SCHEMA_VERSION:
        raise DbVersionError(
            f"banco na versão {version}; esta versão do Pulso conhece até a {SCHEMA_VERSION}"
        )
    for number in range(version + 1, SCHEMA_VERSION + 1):
        conn.execute("BEGIN")
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            for statement in MIGRATIONS[number - 1].split(";"):
                if statement.strip():
                    conn.execute(statement)
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(number),),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        log.info("banco migrado para a versão %d", number)


class HabitStore:
    """Grava e consulta `habit_event`. O relógio de parede (`now`) é injetável nos testes."""

    def __init__(self, conn: sqlite3.Connection, now=datetime.now) -> None:
        self._conn = conn
        self._now = now

    def record(
        self,
        kind: str,
        value: int | None = None,
        category: str | None = None,
        planned_s: int | None = None,
        actual_s: int | None = None,
        excess_s: int | None = None,
    ) -> None:
        """Grava um evento. `category`, `planned_s`, `actual_s` e `excess_s` (v3) só existem nas
        pausas e nas respostas de "o que foi?": é o resumo, nunca o sinal do sensor."""
        stamp = self._now().isoformat(timespec="seconds")
        self._conn.execute(
            "INSERT INTO habit_event (ts, kind, value, category, planned_s, actual_s, excess_s) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (stamp, kind, value, category, planned_s, actual_s, excess_s),
        )

    def count_today(self, kind: str) -> int:
        """Quantos eventos de `kind` aconteceram hoje (hora local)."""
        start = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        row = self._conn.execute(
            "SELECT COUNT(*) FROM habit_event WHERE kind = ? AND ts >= ?",
            (kind, start.isoformat(timespec="seconds")),
        ).fetchone()
        return int(row[0])

    def pending(self, group: str, refuse_points: int, ignore_points: int) -> int:
        """Pendência de `group` ("water" ou "break"): pontos das recusas e omissões **depois** do
        último "fiz". Só o "fiz" zera; "depois" vale 0."""
        done, declined, ignored = PENDING_GROUPS[group]
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) FROM habit_event "
            "WHERE kind IN (?, ?) AND id > COALESCE("
            "(SELECT MAX(id) FROM habit_event WHERE kind = ?), 0) GROUP BY kind",
            (declined, ignored, done),
        ).fetchall()
        counts = dict(rows)
        return counts.get(declined, 0) * refuse_points + counts.get(ignored, 0) * ignore_points

    @property
    def connection(self) -> sqlite3.Connection:
        """A conexão, para o placar dos jogos (`GameStore`) dividir o mesmo arquivo."""
        return self._conn

    def close(self) -> None:
        self._conn.close()


class GameStore:
    """Placar dos jogos: uma linha por rodada, só o resultado (nada de sensor)."""

    def __init__(self, conn: sqlite3.Connection, now=datetime.now) -> None:
        self._conn = conn
        self._now = now

    def record(self, game: str, result: str) -> None:
        stamp = self._now().isoformat(timespec="seconds")
        self._conn.execute(
            "INSERT INTO game_result (ts, game, result) VALUES (?, ?, ?)", (stamp, game, result)
        )

    def totals_today(self) -> dict[str, int]:
        """Vitórias, derrotas e empates **do Pulso** hoje (hora local): `{"won", "lost", ...}`."""
        start = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self._conn.execute(
            "SELECT result, COUNT(*) FROM game_result WHERE ts >= ? GROUP BY result",
            (start.isoformat(timespec="seconds"),),
        ).fetchall()
        counts = dict(rows)
        return {key: int(counts.get(key, 0)) for key in ("won", "lost", "draw")}
