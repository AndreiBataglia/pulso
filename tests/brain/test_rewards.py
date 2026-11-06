"""Regras de recompensa, com relógio falso (nada de esperar de verdade)."""

import pytest

from pulso.brain.rewards import RewardConfig, RewardRules
from pulso.clock import FakeClock
from pulso.sensors.base import SensorFrame


def frame(idle: float = 0.0) -> SensorFrame:
    return SensorFrame(10.0, 40.0, 12.0, idle, "codigo", 1)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def rules(clock) -> RewardRules:
    return RewardRules(clock)


# ---- dono ------------------------------------------------------------------------------------


def test_owner_pet_is_positive_and_scold_is_negative(rules):
    assert rules.owner(+1) > 0
    # (o segundo clique cai no filtro; avançar o tempo está no teste do filtro)


def test_owner_scold_is_negative(rules, clock):
    clock.advance(10)
    assert rules.owner(-1) < 0


def test_repeated_clicks_are_filtered(rules, clock):
    assert rules.owner(+1) == 1.0
    clock.advance(1)
    assert rules.owner(+1) == 0.0  # clique repetido em 1 s: ignorado
    clock.advance(5)
    assert rules.owner(+1) == 1.0  # passou da janela: vale de novo


def test_owner_weighs_more_than_the_rules_by_default():
    cfg = RewardConfig()
    assert cfg.owner_weight > cfg.rules_weight


def test_weights_are_configurable(clock):
    rules = RewardRules(clock, RewardConfig(owner_weight=2.5))
    assert rules.owner(+1) == 2.5


# ---- regras automáticas ----------------------------------------------------------------------


def test_long_idle_and_sleepy_is_rewarded(rules):
    assert rules.evaluate(frame(idle=600), "sonolento") > 0


def test_long_idle_but_other_mood_is_not(rules):
    assert rules.evaluate(frame(idle=600), "animado") == 0.0


def test_short_idle_and_sleepy_is_not(rules):
    assert rules.evaluate(frame(idle=10), "sonolento") == 0.0


def test_rule_has_a_cooldown(rules, clock):
    assert rules.evaluate(frame(idle=600), "sonolento") > 0
    clock.advance(1)
    assert rules.evaluate(frame(idle=601), "sonolento") == 0.0  # ainda no intervalo
    clock.advance(20)
    assert rules.evaluate(frame(idle=620), "sonolento") > 0


def test_return_from_idle_and_cheerful_is_rewarded(rules, clock):
    rules.evaluate(frame(idle=600), "sonolento")
    clock.advance(30)
    assert rules.evaluate(frame(idle=1), "animado") > 0


def test_cheerful_without_a_previous_idle_is_not_rewarded(rules):
    assert rules.evaluate(frame(idle=1), "animado") == 0.0


def test_return_reward_expires(rules, clock):
    rules.evaluate(frame(idle=600), "contente")
    clock.advance(5)
    rules.evaluate(frame(idle=1), "contente")  # voltou
    clock.advance(300)  # bem depois da janela de 60 s
    assert rules.evaluate(frame(idle=1), "animado") == 0.0


def test_worried_after_90_min_without_a_break_is_rewarded(rules, clock):
    for _ in range(91):  # 91 min de trabalho contínuo, uma leitura por minuto
        rules.evaluate(frame(idle=1), "contente")
        clock.advance(60)
    assert rules.evaluate(frame(idle=1), "preocupado") > 0


def test_worried_before_90_min_is_not_rewarded(rules, clock):
    for _ in range(30):
        rules.evaluate(frame(idle=1), "contente")
        clock.advance(60)
    assert rules.evaluate(frame(idle=1), "preocupado") == 0.0


def test_a_break_resets_the_work_clock(rules, clock):
    for _ in range(60):
        rules.evaluate(frame(idle=1), "contente")
        clock.advance(60)
    rules.evaluate(frame(idle=400), "contente")  # pausa de ~7 min
    clock.advance(60)
    for _ in range(40):
        rules.evaluate(frame(idle=1), "contente")
        clock.advance(60)
    # 60 + 40 min no total, mas só 40 desde a pausa: ainda não passou de 90.
    assert rules.evaluate(frame(idle=1), "preocupado") == 0.0


def test_invalid_reading_gives_no_reward(rules):
    assert rules.evaluate(SensorFrame.unknown(), "sonolento") == 0.0


def test_rules_are_scaled_by_their_weight(clock):
    rules = RewardRules(clock, RewardConfig(rules_weight=0.5))
    assert rules.evaluate(frame(idle=600), "sonolento") == 0.5
