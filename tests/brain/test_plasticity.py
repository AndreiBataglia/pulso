"""STDP, elegibilidade e dopamina, isolados do resto da rede (1 pré, 1 pós)."""

import numpy as np

from pulso.brain.plasticity import PlasticityConfig, PlasticSynapses


def make(n_pre: int = 1, n_post: int = 1, w: float = 1.0, **cfg) -> PlasticSynapses:
    return PlasticSynapses(
        np.full((n_pre, n_post), w),
        np.ones((n_pre, n_post), dtype=bool),
        w_max=4.0,
        config=PlasticityConfig(**cfg),
    )


def run(syn: PlasticSynapses, pre_times: list[int], post_times: list[int], steps: int = 60) -> None:
    for t in range(steps):
        syn.update(np.array([float(t in pre_times)]), np.array([float(t in post_times)]))


def two_pre(steps_after: int = 0, dopamine: float = 1.0) -> PlasticSynapses:
    """2 pré → 1 pós; só o pré 0 dispara antes do pós. Aplica a dopamina no fim."""
    syn = make(n_pre=2)
    for t in range(60):
        syn.update(np.array([float(t == 10), 0.0]), np.array([float(t == 15)]))
    for _ in range(steps_after):
        syn.update(np.zeros(2), np.zeros(1))
    syn.apply_dopamine(dopamine)
    return syn


def test_pre_before_post_gives_positive_eligibility():
    syn = make()
    run(syn, pre_times=[10], post_times=[15])
    assert syn.eligibility[0, 0] > 0


def test_post_before_pre_gives_negative_eligibility():
    syn = make()
    run(syn, pre_times=[15], post_times=[10])
    assert syn.eligibility[0, 0] < 0


def test_closer_in_time_means_stronger_effect():
    near, far = make(), make()
    run(near, [10], [12])
    run(far, [10], [40])
    assert near.eligibility[0, 0] > far.eligibility[0, 0] > 0


def test_stdp_alone_never_changes_the_weight():
    syn = make()
    run(syn, [10], [15])
    assert syn.w[0, 0] == 1.0  # só a elegibilidade guarda o resultado


def test_without_dopamine_the_weight_does_not_change():
    syn = make()
    run(syn, [10], [15])
    syn.apply_dopamine(0.0)
    assert syn.w[0, 0] == 1.0


def test_positive_dopamine_strengthens_eligible_synapses():
    syn = two_pre(dopamine=1.0)
    assert syn.w[0, 0] > 1.0 > syn.w[1, 0]


def test_negative_dopamine_flips_the_effect():
    syn = two_pre(dopamine=-1.0)
    assert syn.w[0, 0] < 1.0 < syn.w[1, 0]


def test_dopamine_changes_only_eligible_synapses():
    # 2 pré → 1 pós, mas só o pré 0 participa do disparo.
    syn = make(n_pre=2)
    for t in range(60):
        pre = np.array([float(t == 10), 0.0])
        syn.update(pre, np.array([float(t == 15)]))
    syn.apply_dopamine(1.0)
    assert syn.w[0, 0] > syn.w[1, 0]


def test_delayed_reward_still_finds_the_synapse():
    """A elegibilidade dura ~τe de REDE: a dopamina atrasada (500 ms) ainda acha a sinapse."""
    syn = two_pre(steps_after=500)
    assert syn.w[0, 0] > 1.0 > syn.w[1, 0]


def test_eligibility_fades_with_the_network_time_constant():
    syn = make(tau_e_net_ms=100.0)
    run(syn, [10], [15], steps=30)
    before = syn.eligibility[0, 0]
    for _ in range(1000):
        syn.update(np.zeros(1), np.zeros(1))
    assert abs(syn.eligibility[0, 0]) < abs(before) * 1e-3


def test_weights_stay_within_bounds():
    syn = make(w=3.9)
    run(syn, [10], [15])
    for _ in range(200):
        syn.apply_dopamine(10.0)
    assert 0.0 <= syn.w[0, 0] <= 4.0


def test_missing_connections_stay_missing():
    mask = np.array([[True, False]])
    syn = PlasticSynapses(np.array([[1.0, 1.0]]), mask, w_max=4.0)
    for t in range(60):
        syn.update(np.array([float(t == 10)]), np.array([float(t == 15)] * 2))
    syn.apply_dopamine(1.0)
    assert syn.w[0, 1] == 0.0


def test_normalization_keeps_the_input_sum_of_each_post_neuron():
    syn = make(n_pre=3, w=1.0)
    for t in range(60):
        pre = np.array([float(t == 10), 0.0, 0.0])
        syn.update(pre, np.array([float(t == 15)]))
    syn.apply_dopamine(1.0)
    assert np.isclose(syn.w.sum(), 3.0)
    assert syn.w[0, 0] > syn.w[1, 0]  # o beneficiado ganhou, os outros cederam
