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
        array[...] = 0
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


# ---- recompensa (etapa 3) ---------------------------------------------------------------------


def test_reward_after_activity_changes_the_state(make_engine):
    engine = make_engine(1)
    engine.step(strong_input(engine), 500)
    before = engine.state_dict()
    engine.reward(1.0)
    after = engine.state_dict()
    assert any(not np.array_equal(before[k], after[k]) for k in before)


def test_reward_with_a_silent_network_changes_no_weight(make_engine):
    """Sem atividade não há o que reforçar: nada de peso muda (a média r̄ pode mudar)."""
    engine = make_engine(1)
    engine.step(np.zeros(engine.n_inputs), 500)
    before = engine.state_dict()
    engine.reward(1.0)
    after = engine.state_dict()
    for key in before:
        if key.startswith("w_"):
            assert np.array_equal(before[key], after[key]), key


def test_reward_keeps_the_network_working(make_engine):
    engine = make_engine(1)
    engine.step(strong_input(engine), 300)
    for value in (1.0, -1.0, 0.5, 0.0):
        engine.reward(value)
    result = engine.step(strong_input(engine), 100)
    assert result.counts.shape == (len(engine.groups),)


def test_reward_survives_save_and_load(make_engine):
    """O que o reward mudou (pesos e r̄) é o que o state_dict guarda."""
    trained = make_engine(1)
    trained.step(strong_input(trained), 500)
    trained.reward(1.0)
    fresh = make_engine(2)
    fresh.load_state_dict(trained.state_dict())
    for key, value in trained.state_dict().items():
        assert np.array_equal(value, fresh.state_dict()[key]), key


def test_loaded_network_wakes_up_with_clean_traces(make_engine):
    """Carregar do disco é "acordar": o primeiro reward não pode usar rastros antigos."""
    a, b = make_engine(1), make_engine(1)
    a.step(strong_input(a), 500)  # a tem elegibilidade acumulada
    a.load_state_dict(b.state_dict())
    before = a.state_dict()
    a.reward(1.0)
    for key, value in a.state_dict().items():
        if key.startswith("w_"):
            assert np.array_equal(before[key], value), key


# ---- snapshot para os gráficos (etapa 5) -------------------------------------------------------


def test_snapshot_grows_with_the_simulated_time_and_stays_bounded(make_engine):
    engine = make_engine(1)
    assert engine.snapshot().spikes.shape[1] == 0  # nada simulado ainda
    engine.step(strong_input(engine), 300)
    snap = engine.snapshot()
    assert snap.spikes.shape[1] == 300 == snap.voltage.shape[1]
    engine.step(strong_input(engine), 5000)
    assert engine.snapshot().spikes.shape[1] <= 5000  # janela limitada (memória não cresce)
    assert engine.snapshot().spikes.shape[1] == engine.snapshot().voltage.shape[1]


def test_snapshot_rows_match_the_declared_layers(make_engine):
    engine = make_engine(1)
    engine.step(strong_input(engine), 200)
    snap = engine.snapshot()
    assert snap.layers[0][1] == 0 and snap.layers[-1][2] == snap.spikes.shape[0]
    assert [name for name, *_ in snap.layers][-1] == "saida"
    start, stop = snap.layers[-1][1:]
    assert stop - start == snap.group_size * len(snap.groups)
    assert snap.voltage.shape[0] == len(snap.voltage_labels) == 3
    assert snap.weights.shape[1] == snap.group_size * len(snap.groups)


def test_snapshot_spikes_agree_with_step_counts(make_engine):
    """O que o raster mostra é o que a rede disparou: a soma da saída bate com `counts`."""
    engine = make_engine(1)
    result = engine.step(strong_input(engine), 500)
    snap = engine.snapshot()
    start, stop = snap.layers[-1][1:]
    assert int(snap.spikes[start:stop].sum()) == int(result.counts.sum())
    assert result.counts.sum() > 0


def test_snapshot_keeps_time_order_after_wrapping(make_engine):
    """Depois de a janela dar a volta, a coluna mais nova continua sendo a última."""
    engine = make_engine(1)
    engine.step(strong_input(engine), 3000)  # passa do tamanho do registro
    engine.step(np.zeros(engine.n_inputs), 50)  # e os últimos 50 ms são de silêncio na entrada
    snap = engine.snapshot()
    start, stop = snap.layers[0][1:]
    assert not snap.spikes[start:stop, -50:].any()
    assert snap.spikes[start:stop, :-50].any()


def test_snapshot_is_a_copy(make_engine):
    engine = make_engine(1)
    engine.step(strong_input(engine), 100)
    snap = engine.snapshot()
    snap.weights[...] = 0
    snap.spikes[...] = False
    assert engine.snapshot().weights.any() and engine.snapshot().spikes.any()


def test_reward_returns_the_dopamine_and_snapshot_shows_it(make_engine):
    engine = make_engine(1)
    assert engine.snapshot().dopamine == 0.0
    d = engine.reward(1.0)
    assert d == pytest.approx(1.0)  # r̄ ainda 0: tudo é surpresa
    snap = engine.snapshot()
    assert snap.dopamine == d and snap.rewards == (1, 0)
    d2 = engine.reward(1.0)
    assert 0 < d2 < d  # já esperava parte da recompensa: a surpresa diminui


def test_snapshot_after_loading_starts_blank(make_engine):
    a, b = make_engine(1), make_engine(2)
    a.step(strong_input(a), 200)
    a.load_state_dict(b.state_dict())
    assert a.snapshot().spikes.shape[1] == 0
