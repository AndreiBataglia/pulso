"""O banco de hábitos: migração v1, gravação e a pendência calculada dos eventos."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from pulso.habits import kinds
from pulso.storage.db import SCHEMA_VERSION, DbVersionError, HabitStore, open_db


@pytest.fixture
def store():
    now = [datetime(2026, 11, 6, 10, 0, 0)]
    s = HabitStore(open_db(":memory:"), now=lambda: now[0])
    s.clock = now  # os testes andam o relógio de parede por aqui
    return s


def test_banco_novo_nasce_na_versao_1(tmp_path):
    conn = open_db(tmp_path / "sub" / "pulso.db")  # cria a pasta
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert SCHEMA_VERSION == 1 and row[0] == "1"
    conn.close()


def test_reabrir_nao_refaz_a_migracao_nem_perde_eventos(tmp_path):
    path = tmp_path / "pulso.db"
    first = open_db(path)
    HabitStore(first).record(kinds.WATER_DRUNK)
    first.close()
    conn = open_db(path)
    assert conn.execute("SELECT COUNT(*) FROM habit_event").fetchone()[0] == 1
    conn.close()


def test_banco_de_versao_mais_nova_e_recusado(tmp_path):
    path = tmp_path / "pulso.db"
    conn = open_db(path)
    conn.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
    conn.close()
    with pytest.raises(DbVersionError):
        open_db(path)


def test_check_recusa_tipo_desconhecido(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.record("inventado")


@pytest.mark.parametrize("kind", kinds.ALL_KINDS)
def test_todos_os_tipos_sao_aceitos(store, kind):
    store.record(kind)


def test_contagem_de_hoje_ignora_ontem(store):
    store.clock[0] = datetime(2026, 11, 5, 23, 0)
    store.record(kinds.WATER_DRUNK)
    store.clock[0] = datetime(2026, 11, 6, 8, 0)
    store.record(kinds.WATER_DRUNK)
    store.record(kinds.WATER_DRUNK)
    store.record(kinds.FOCUS_DONE)
    assert store.count_today(kinds.WATER_DRUNK) == 2
    assert store.count_today(kinds.FOCUS_DONE) == 1


def _pending(store, group="water"):
    return store.pending(group, refuse_points=2, ignore_points=1)


def test_pendencia_recusei_2_ignorei_1_depois_0(store):
    store.record(kinds.WATER_DECLINED)
    assert _pending(store) == 2
    store.record(kinds.WATER_IGNORED)
    assert _pending(store) == 3
    store.record(kinds.WATER_SNOOZED)
    assert _pending(store) == 3  # "depois" não soma


def test_so_o_fiz_zera_a_pendencia(store):
    for kind in (kinds.WATER_DECLINED, kinds.WATER_DECLINED, kinds.WATER_IGNORED):
        store.record(kind)
    assert _pending(store) == 5
    store.record(kinds.WATER_SNOOZED)
    store.record(kinds.FOCUS_DONE)
    assert _pending(store) == 5
    store.record(kinds.WATER_DRUNK)
    assert _pending(store) == 0


def test_agua_e_pausa_tem_pendencias_separadas(store):
    store.record(kinds.WATER_DECLINED)
    store.record(kinds.BREAK_IGNORED)
    assert _pending(store, "water") == 2
    assert _pending(store, "break") == 1
    store.record(kinds.BREAK_DONE)
    assert _pending(store, "water") == 2 and _pending(store, "break") == 0


def test_a_pendencia_nao_esfria_com_o_tempo_e_sobrevive_ao_reabrir(tmp_path):
    path = tmp_path / "pulso.db"
    now = datetime(2026, 11, 6, 10, 0)
    conn = open_db(path)
    HabitStore(conn, now=lambda: now).record(kinds.WATER_DECLINED)
    conn.close()
    later = HabitStore(open_db(path), now=lambda: now + timedelta(days=3))
    assert later.pending("water", 2, 1) == 2
    later.close()
