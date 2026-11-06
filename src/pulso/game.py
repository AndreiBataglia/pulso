"""Os jogos do dia a dia: jokenpô e par ou ímpar. Só regras, sem Qt e sem banco.

O Pulso joga **limpo**: escolhe ao acaso, sem espiar a jogada do dono (nos testes, o
`random.Random` é injetado). O resultado é sempre do ponto de vista do Pulso: ganhou, perdeu ou
empatou. Ele mexe só na expressão do rosto, nunca na rede: ganhar ou perder é sorte e entraria
como ruído no que ela aprende.
"""

import random
from dataclasses import dataclass

WON, LOST, DRAW = "won", "lost", "draw"  # do ponto de vista do Pulso

ROCK, PAPER, SCISSORS = "pedra", "papel", "tesoura"
RPS_MOVES = (ROCK, PAPER, SCISSORS)
RPS_EMOJI = {ROCK: "✊", PAPER: "✋", SCISSORS: "✌️"}
_BEATS = {ROCK: SCISSORS, PAPER: ROCK, SCISSORS: PAPER}  # a chave vence o valor

EVEN, ODD = "par", "ímpar"
MAX_FINGERS = 5  # de 0 a 5 dedos


@dataclass(frozen=True)
class Round:
    """Uma rodada: o que cada um jogou e como acabou para o Pulso."""

    game: str  # "rps" ou "evenodd"
    owner: str
    pet: str
    result: str


def rps(owner: str, rng: random.Random) -> Round:
    """Jokenpô: o dono jogou `owner`; o Pulso sorteia a dele."""
    if owner not in RPS_MOVES:
        raise ValueError(f"jogada desconhecida: {owner!r}")
    pet = rng.choice(RPS_MOVES)
    if owner == pet:
        result = DRAW
    else:
        result = WON if _BEATS[pet] == owner else LOST
    return Round("rps", owner, pet, result)


def even_odd(choice: str, fingers: int, rng: random.Random) -> Round:
    """Par ou ímpar: o dono escolhe `choice` e mostra `fingers`; o Pulso mostra a dele. O Pulso fica
    com o que sobrou. Soma par → "par" ganha; soma ímpar → "ímpar" ganha. Nunca empata."""
    if choice not in (EVEN, ODD):
        raise ValueError(f"escolha desconhecida: {choice!r}")
    if not 0 <= fingers <= MAX_FINGERS:
        raise ValueError(f"dedos fora de 0 a {MAX_FINGERS}: {fingers!r}")
    pet = rng.randint(0, MAX_FINGERS)
    winner = EVEN if (fingers + pet) % 2 == 0 else ODD
    result = LOST if winner == choice else WON
    return Round("evenodd", f"{choice} {fingers}", str(pet), result)
