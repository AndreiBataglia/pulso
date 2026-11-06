import numpy as np

from pulso.brain.encoding import (
    CATEGORIES,
    MAX_RATE_HZ,
    N_INPUTS,
    REPEAT,
    encode,
)
from pulso.brain.numpy_engine import DEFAULT_GROUPS, NetworkConfig
from pulso.sensors.base import SensorFrame


def frame(**kw) -> SensorFrame:
    base = dict(
        cpu_percent=0.0,
        ram_percent=0.0,
        hour_of_day=0.0,
        idle_seconds=0.0,
        category="outro",
        app_switches_last_min=0,
    )
    return SensorFrame(**{**base, **kw})


def test_size_matches_the_engine_default():
    assert encode(frame()).shape == (N_INPUTS,)
    assert NetworkConfig().n_inputs == N_INPUTS


def test_rates_stay_within_range():
    extreme = frame(
        cpu_percent=500, ram_percent=-5, idle_seconds=1e9, app_switches_last_min=999, hour_of_day=99
    )
    rates = encode(extreme)
    assert rates.min() >= 0.0
    assert rates.max() <= MAX_RATE_HZ


def test_scalar_has_high_and_low_groups():
    low = encode(frame(cpu_percent=0))
    high = encode(frame(cpu_percent=100))
    # Os primeiros REPEAT neurônios são "cpu alta"; os REPEAT seguintes, "cpu baixa".
    assert low[:REPEAT].tolist() == [0.0] * REPEAT
    assert high[:REPEAT].tolist() == [MAX_RATE_HZ] * REPEAT
    assert low[REPEAT : 2 * REPEAT].tolist() == [MAX_RATE_HZ] * REPEAT
    assert high[REPEAT : 2 * REPEAT].tolist() == [0.0] * REPEAT


def test_category_is_one_hot():
    a = encode(frame(category="codigo"))
    b = encode(frame(category="navegador"))
    assert not np.array_equal(a, b)
    assert np.count_nonzero(a - b) == 2 * REPEAT  # sai um grupo, entra outro


def test_unknown_category_falls_back_to_other():
    assert np.array_equal(encode(frame(category="marciano")), encode(frame(category="outro")))
    assert "outro" in CATEGORIES


def test_hour_bands_change_the_pattern():
    assert not np.array_equal(encode(frame(hour_of_day=2.0)), encode(frame(hour_of_day=14.0)))
    # Dentro da mesma faixa de 4 h, o padrão é igual.
    assert np.array_equal(encode(frame(hour_of_day=12.1)), encode(frame(hour_of_day=15.9)))


def test_invalid_frame_is_silence():
    assert not encode(SensorFrame.unknown()).any()


def test_engine_default_groups_are_the_moods():
    assert DEFAULT_GROUPS == ("animado", "contente", "entediado", "sonolento", "preocupado")
