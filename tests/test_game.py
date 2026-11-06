"""Os jogos: regras do jokenpô e do par ou ímpar, e o placar no banco."""

import random
import sqlite3
from datetime import datetime

import pytest

from pulso import game
from pulso.storage.db import GameStore, open_db


class FixedRng(random.Random):
    """Sorteio combinado: `choice` e `randint` devolvem o que for pedido."""

    def __init__(self, value):
        super().__init__(1)
        self.value = value

    def choice(self, seq):
        return self.value

    def randint(self, a, b):
        return self.value


@pytest.mark.parametrize(
    ("owner", "pet", "result"),
    [
        (game.ROCK, game.SCISSORS, game.LOST),  # a pedra do dono quebra a tesoura: o pet perde
        (game.PAPER, game.ROCK, game.LOST),
        (game.SCISSORS, game.PAPER, game.LOST),
        (game.ROCK, game.PAPER, game.WON),
        (game.PAPER, game.SCISSORS, game.WON),
        (game.SCISSORS, game.ROCK, game.WON),
        (game.ROCK, game.ROCK, game.DRAW),
        (game.PAPER, game.PAPER, game.DRAW),
        (game.SCISSORS, game.SCISSORS, game.DRAW),
    ],
)
def test_jokenpo_resultado_do_ponto_de_vista_do_pet(owner, pet, result):
    played = game.rps(owner, FixedRng(pet))
    assert (played.owner, played.pet, played.result) == (owner, pet, result)


def test_jokenpo_recusa_jogada_inventada():
    with pytest.raises(ValueError):
        game.rps("fogo", random.Random(1))


@pytest.mark.parametrize(
    ("choice", "fingers", "pet", "result"),
    [
        (game.EVEN, 2, 4, game.LOST),  # 6 é par: quem escolheu par ganha, o pet perde
        (game.EVEN, 2, 3, game.WON),  # 5 é ímpar: o dono escolheu par e perdeu
        (game.ODD, 2, 3, game.LOST),
        (game.ODD, 1, 1, game.WON),
        (game.EVEN, 0, 0, game.LOST),  # 0 + 0 = 0, par
    ],
)
def test_par_ou_impar_soma_e_paridade(choice, fingers, pet, result):
    played = game.even_odd(choice, fingers, FixedRng(pet))
    assert played.result == result and played.pet == str(pet)


def test_par_ou_impar_nunca_empata_e_valida_a_entrada():
    results = {game.even_odd(game.EVEN, f, random.Random(f)).result for f in range(6)}
    assert game.DRAW not in results
    with pytest.raises(ValueError):
        game.even_odd("meio", 1, random.Random(1))
    with pytest.raises(ValueError):
        game.even_odd(game.EVEN, 6, random.Random(1))


def test_o_pet_joga_limpo_todas_as_jogadas_saem_com_o_tempo():
    rng = random.Random(7)
    seen = {game.rps(game.ROCK, rng).pet for _ in range(60)}
    assert seen == set(game.RPS_MOVES)


def test_placar_do_dia_conta_do_ponto_de_vista_do_pet():
    store = GameStore(open_db(":memory:"), now=lambda: datetime(2026, 11, 6, 10, 0))
    assert store.totals_today() == {"won": 0, "lost": 0, "draw": 0}
    store.record("rps", "won")
    store.record("rps", "won")
    store.record("evenodd", "lost")
    store.record("rps", "draw")
    assert store.totals_today() == {"won": 2, "lost": 1, "draw": 1}


def test_o_banco_recusa_jogo_ou_resultado_inventado():
    conn = open_db(":memory:")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO game_result (ts, game, result) VALUES ('x', 'xadrez', 'won')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO game_result (ts, game, result) VALUES ('x', 'rps', 'quem')")
