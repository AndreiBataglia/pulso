import numpy as np
import pytest

from pulso.brain.decoding import MoodDecoder

MOODS = ["a", "b", "c"]


def feed(decoder: MoodDecoder, counts: list[int], times: int = 10) -> str | None:
    """Entrega a mesma contagem `times` vezes e devolve o resultado da última chamada."""
    result = None
    for _ in range(times):
        result = decoder.update(np.array(counts))
    return result


def test_decides_only_when_the_window_closes():
    decoder = MoodDecoder(MOODS, window_steps=10)
    assert all(decoder.update(np.array([1, 5, 1])) is None for _ in range(9))
    assert decoder.update(np.array([1, 5, 1])) == "b"


def test_most_active_group_wins():
    decoder = MoodDecoder(MOODS)
    assert feed(decoder, [3, 1, 9]) == "c"
    assert decoder.mood == "c"


def test_hysteresis_blocks_a_narrow_win():
    decoder = MoodDecoder(MOODS, margin=0.25, initial="a")
    # b tem só 10% a mais que a: não derruba o humor atual.
    assert feed(decoder, [10, 11, 0]) == "a"


def test_hysteresis_lets_a_clear_win_through():
    decoder = MoodDecoder(MOODS, margin=0.25, initial="a")
    assert feed(decoder, [10, 14, 0]) == "b"


def test_silent_network_keeps_the_mood():
    decoder = MoodDecoder(MOODS, initial="b")
    assert feed(decoder, [0, 0, 0]) == "b"


def test_silent_network_without_mood_stays_undecided():
    assert feed(MoodDecoder(MOODS), [0, 0, 0]) is None


def test_window_sums_the_whole_interval():
    decoder = MoodDecoder(MOODS)
    for counts in ([9, 0, 0], [0, 4, 0], [0, 4, 0], [0, 4, 0]):
        decoder.update(np.array(counts))
    # Total da janela: a = 9, b = 12. Vence b, embora a tenha tido a volta mais forte sozinha.
    for _ in range(6):
        result = decoder.update(np.array([0, 0, 0]))
    assert result == "b"


def test_unknown_initial_mood_is_rejected():
    with pytest.raises(ValueError):
        MoodDecoder(MOODS, initial="z")
