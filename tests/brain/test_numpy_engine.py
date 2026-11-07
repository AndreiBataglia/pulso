"""Comportamento específico do motor numpy (o que o contrato genérico não cobre)."""

import time

import numpy as np

from pulso.brain.decoding import MoodDecoder
from pulso.brain.encoding import encode
from pulso.brain.numpy_engine import NumpyEngine
from pulso.sensors.fake import demo_scenario

BUDGET_MS_PER_SECOND = 20.0  # TRD §5.1


def run_scenario(seed: int) -> list[str]:
    """Roda o roteiro de 4 momentos (60 s cada) e devolve o humor decidido a cada 10 s."""
    engine = NumpyEngine(seed=seed)
    decoder = MoodDecoder(engine.groups)
    moods = []
    for frame in demo_scenario(60):
        mood = decoder.update(engine.step(encode(frame), 100).counts)
        if mood is not None:
            moods.append(mood)
    return moods


def test_scenario_makes_a_decision_every_10_seconds():
    assert len(run_scenario(1)) == 24  # 240 s / 10 s


def test_mood_changes_when_the_sensor_script_changes():
    # Com pesos sorteados (ainda sem aprender) a decisão depende da semente; com só 2 grupos, uma
    # parte delas escolhe o mesmo para todos os contextos. Medido: 5 de 10 sementes mudam de
    # decisão; exigimos 3 para não ser frágil.
    changed = sum(len(set(run_scenario(seed))) >= 2 for seed in range(10))
    assert changed >= 3


def test_wiring_is_sparse_and_signed():
    engine = NumpyEngine(seed=1)
    n_e = engine.config.n_hidden_e
    w = engine.w_hidden_hidden
    assert (w[:n_e] >= 0).all() and (w[n_e:] <= 0).all()  # excitatórios ≥ 0, inibitórios ≤ 0
    assert np.diag(w).tolist() == [0.0] * w.shape[0]
    density = np.count_nonzero(engine.w_in_hidden) / engine.w_in_hidden.size
    assert 0.15 < density < 0.25
    assert not engine.w_hidden_out[n_e:].any()  # inibitórios não falam com a saída


def test_lateral_inhibition_only_between_different_groups():
    engine = NumpyEngine(seed=1)
    size = engine.config.group_size
    w = engine.w_out_out
    assert (w[:size, :size] == 0).all()  # dentro do mesmo grupo: nada
    assert (w[:size, size : 2 * size] < 0).all()  # entre grupos: inibição


def test_weights_do_not_change_while_running():
    # Sem dopamina o STDP só enche a elegibilidade: os pesos ficam idênticos depois de simular.
    engine = NumpyEngine(seed=1)
    before = engine.state_dict()
    engine.step(np.full(engine.n_inputs, 80.0), 1000)
    after = engine.state_dict()
    assert all(np.array_equal(before[k], after[k]) for k in before if k != "stats")
    assert after["stats"][2] == before["stats"][2] + 1000  # só o contador de passos anda


def test_cost_of_one_real_second_fits_the_budget():
    engine = NumpyEngine(seed=1)
    rates = encode(demo_scenario(1)[0])
    engine.step(rates, 100)  # aquece
    runs = 30
    start = time.perf_counter()
    for _ in range(runs):
        engine.step(rates, 100)
    ms_per_second = (time.perf_counter() - start) / runs * 1000
    assert ms_per_second < BUDGET_MS_PER_SECOND
