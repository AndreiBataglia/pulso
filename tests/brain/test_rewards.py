"""Recompensas do dono e dos hábitos, com relógio falso (nada de esperar de verdade)."""

import pytest

from pulso.brain.rewards import RewardConfig, RewardRules
from pulso.clock import FakeClock
from pulso.habits import kinds


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


def test_weights_are_configurable(clock):
    rules = RewardRules(clock, RewardConfig(owner_weight=2.5))
    assert rules.owner(+1) == 2.5


def test_habito_pesa_como_o_dono():
    rules = RewardRules(FakeClock())
    assert rules.habit(kinds.WATER_DRUNK) == 1.0
    assert rules.habit(kinds.BREAK_DECLINED) == -1.0
    assert rules.habit(kinds.WATER_IGNORED) == -0.5
    assert rules.habit(kinds.BREAK_ACCEPTED) == 1.0


# ---- prorrogação com peso crescente -----------------------------------------------------------


@pytest.mark.parametrize(
    ("vez", "valor"), [(1, -0.25), (2, -0.5), (3, -0.75), (4, -1.0), (9, -1.0)]
)
def test_cada_prorrogacao_pesa_mais_ate_o_peso_de_uma_recusa(rules, vez, valor):
    assert rules.habit(kinds.BREAK_SNOOZED, vez) == pytest.approx(valor)


def test_prorrogar_nunca_pesa_mais_que_recusar(rules):
    assert rules.habit(kinds.BREAK_SNOOZED, 99) >= rules.habit(kinds.BREAK_DECLINED)
