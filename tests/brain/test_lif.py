"""Neurônio LIF isolado: corrente constante → frequência dentro da faixa teórica."""

import math

import numpy as np
import pytest

from pulso.brain.lif import LIFParams, LIFPopulation

PARAMS = LIFParams()


def simulate_rate_hz(drive_mv: float, duration_ms: int = 2000) -> float:
    """Frequência de disparo de um neurônio sozinho, com um empurrão constante `drive_mv`."""
    neuron = LIFPopulation(1, PARAMS)
    spikes = 0
    for _ in range(duration_ms):
        spikes += int(neuron.step(np.zeros(1), drive_mv=drive_mv).sum())
    return spikes * 1000.0 / duration_ms


def theoretical_rate_hz(drive_mv: float) -> float:
    """Frequência exata do LIF contínuo: ISI = t_ref + tau * ln(D / (D - gap))."""
    gap = PARAMS.v_threshold_mv - PARAMS.v_rest_mv
    isi_ms = PARAMS.t_ref_ms + PARAMS.tau_m_ms * math.log(drive_mv / (drive_mv - gap))
    return 1000.0 / isi_ms


@pytest.mark.parametrize("drive_mv", [20.0, 30.0, 50.0])
def test_constant_drive_matches_theory(drive_mv):
    measured = simulate_rate_hz(drive_mv)
    expected = theoretical_rate_hz(drive_mv)
    # Euler com passo de 1 ms erra um pouco; 10% de folga cobre isso com sobra.
    assert measured == pytest.approx(expected, rel=0.10)


def test_below_threshold_never_fires():
    # O empurrão de 14 mV leva V a -51 mV, abaixo do limiar de -50 mV: nunca dispara.
    assert simulate_rate_hz(14.0) == 0.0


def test_stronger_drive_fires_faster():
    rates = [simulate_rate_hz(d) for d in (20.0, 30.0, 50.0)]
    assert rates == sorted(rates)
    assert rates[0] < rates[-1]


def test_refractory_period_limits_rate():
    # Mesmo com um empurrão absurdo, o refratário de 2 ms impõe um teto de 500 Hz (1000 / t_ref).
    assert simulate_rate_hz(10_000.0) <= 1000.0 / PARAMS.t_ref_ms


def test_synaptic_jump_can_trigger_spike_and_resets():
    neuron = LIFPopulation(1, PARAMS)
    spiked = neuron.step(np.array([20.0]))  # salto de 20 mV > 15 mV de distância ao limiar
    assert spiked.tolist() == [True]
    assert neuron.v[0] == PARAMS.v_reset_mv


def test_no_input_stays_at_rest():
    neuron = LIFPopulation(3, PARAMS)
    for _ in range(100):
        assert not neuron.step(np.zeros(3)).any()
    assert np.allclose(neuron.v, PARAMS.v_rest_mv)
