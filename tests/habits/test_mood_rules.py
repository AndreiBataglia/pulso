"""Humor por regras: um teste por regra, mais a prioridade entre elas."""

import dataclasses

import pytest

from pulso.habits import mood_rules as r

CALMO = r.MoodInputs(
    nervous_reason=None,
    postponements=0,
    idle_s=0.0,
    sleepy_after_s=300.0,
    on_time_breaks=0,
    cups=0,
)


def _with(**kw) -> r.MoodVerdict:
    return r.decide(dataclasses.replace(CALMO, **kw))


def test_sem_nada_o_rosto_fica_neutro_e_tranquilo():
    assert _with() == r.MoodVerdict("neutro", r.CALM)


def test_pendencia_deixa_nervoso_e_diz_o_que_ficou_pendente():
    v = _with(nervous_reason="água e pausa")
    assert (v.mood, v.cause, v.detail) == ("nervoso", r.PENDING, "água e pausa")


def test_lembrete_prorrogado_deixa_preocupado_e_conta_as_vezes():
    v = _with(postponements=2)
    assert (v.mood, v.cause, v.detail) == ("preocupado", r.POSTPONED, 2)


def test_muito_tempo_sem_interacao_deixa_sonolento_com_os_minutos():
    v = _with(idle_s=7 * 60 + 5)
    assert (v.mood, v.cause, v.detail) == ("sonolento", r.SLEEPY, 7)


def test_logo_abaixo_do_limite_ainda_nao_e_sonolento():
    assert _with(idle_s=299.0).mood == "neutro"


def test_observacao_pausada_nao_tem_ociosidade_para_julgar():
    assert _with(idle_s=None).mood == "neutro"


def test_pausa_no_horario_deixa_contente():
    v = _with(on_time_breaks=2)
    assert (v.mood, v.cause, v.detail) == ("contente", r.ON_TIME_BREAK, 2)


def test_copo_dagua_hoje_deixa_contente():
    v = _with(cups=3)
    assert (v.mood, v.cause, v.detail) == ("contente", r.WATER_DONE, 3)


@pytest.mark.parametrize(
    ("forte", "fraco"),
    [
        (dict(nervous_reason="água"), dict(postponements=1, idle_s=900.0, on_time_breaks=1)),
        (dict(postponements=1), dict(idle_s=900.0, on_time_breaks=1, cups=1)),
        (dict(idle_s=900.0), dict(on_time_breaks=1, cups=1)),
        (dict(on_time_breaks=1), dict(cups=1)),
    ],
)
def test_a_regra_mais_forte_ganha(forte, fraco):
    assert _with(**forte, **fraco) == _with(**forte)


def test_a_chave_ignora_o_detalhe_que_muda_a_cada_minuto():
    assert _with(idle_s=400.0).key == _with(idle_s=700.0).key
