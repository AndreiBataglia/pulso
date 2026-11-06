"""Contrato do `Engine`: roda os mesmos cenários contra QUALQUER motor.

Para aceitar um motor novo, basta acrescentar a fábrica dele em `ENGINE_FACTORIES`.
"""

import numpy as np
import pytest

from pulso.brain.numpy_engine import NumpyEngine

ENGINE_FACTORIES = {"numpy": lambda seed: NumpyEngine(seed=seed)}


@pytest.fixture(params=list(ENGINE_FACTORIES))
def make_engine(request):
    return ENGINE_FACTORIES[request.param]


def strong_input(engine) -> np.ndarray:
    return np.full(engine.n_inputs, 60.0)


def test_declares_inputs_and_groups(make_engine):
    engine = make_engine(1)
    assert engine.n_inputs > 0
    assert len(engine.groups) >= 2
    assert len(set(engine.groups)) == len(engine.groups)


def test_step_returns_one_count_per_group(make_engine):
    engine = make_engine(1)
    result = engine.step(strong_input(engine), 100)
    assert result.counts.shape == (len(engine.groups),)
    assert (result.counts >= 0).all()
    assert result.hidden_spikes >= 0


def test_silence_produces_no_spikes(make_engine):
    engine = make_engine(1)
    result = engine.step(np.zeros(engine.n_inputs), 100)
    assert result.counts.sum() == 0
    assert result.hidden_spikes == 0


def test_strong_input_makes_the_network_fire(make_engine):
    engine = make_engine(1)
    result = engine.step(strong_input(engine), 1000)
    assert result.hidden_spikes > 0
    assert result.counts.sum() > 0


def test_same_seed_same_behaviour(make_engine):
    a, b = make_engine(7), make_engine(7)
    rates = np.linspace(0, 100, a.n_inputs)
    for _ in range(3):
        assert a.step(rates, 100).counts.tolist() == b.step(rates, 100).counts.tolist()


def test_different_seeds_differ(make_engine):
    a, b = make_engine(1), make_engine(2)
    rates = strong_input(a)
    assert a.step(rates, 1000).counts.tolist() != b.step(rates, 1000).counts.tolist()


def test_wrong_input_size_is_rejected(make_engine):
    engine = make_engine(1)
    with pytest.raises(ValueError):
        engine.step(np.zeros(engine.n_inputs + 1), 100)


def test_state_roundtrip_keeps_weights(make_engine):
    original = make_engine(1)
    other = make_engine(2)
    state = original.state_dict()
    other.load_state_dict(state)
    restored = other.state_dict()
    assert state.keys() == restored.keys()
    for key in state:
        assert np.array_equal(state[key], restored[key])


def test_state_dict_is_a_copy(make_engine):
    engine = make_engine(1)
    state = engine.state_dict()
    for array in state.values():
        array[:] = 0
    assert any(np.any(v != 0) for v in engine.state_dict().values())


def test_incompatible_state_is_rejected(make_engine):
    engine = make_engine(1)
    state = engine.state_dict()
    first = next(iter(state))
    bad = {**state, first: np.zeros((1, 1))}
    with pytest.raises(ValueError):
        engine.load_state_dict(bad)
    with pytest.raises(ValueError):
        engine.load_state_dict({})
