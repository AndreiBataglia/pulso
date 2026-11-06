"""A aba Jogo: o pet fica contente ao ganhar e bravo ao perder, e o placar sobe."""

import random

import pytest

from pulso import game
from pulso.storage.db import GameStore, open_db
from pulso.ui.game_tab import GameTab


class FixedRng(random.Random):
    def __init__(self, value):
        super().__init__(1)
        self.value = value

    def choice(self, seq):
        return self.value

    def randint(self, a, b):
        return self.value


@pytest.fixture
def make_tab(qapp):
    tabs = []

    def make(value):
        tab = GameTab(GameStore(open_db(":memory:")), FixedRng(value))
        tab.resize(300, 480)
        tab.show()
        tabs.append(tab)
        return tab

    yield make
    for tab in tabs:
        tab.close()


def test_pet_ganha_fica_contente_e_o_placar_sobe(make_tab):
    tab = make_tab(game.PAPER)  # o pet joga papel
    played = tab.play_rps(game.ROCK)  # contra pedra: papel embrulha, o pet ganha
    assert played.result == game.WON
    assert tab.face.shown == "contente"
    assert "Ganhei" in tab.result.text()
    assert "Pulso 1 × 0 você" in tab.score.text()


def test_pet_perde_fica_bravo_e_depois_volta_ao_humor(make_tab):
    tab = make_tab(game.SCISSORS)
    tab.face.set_mood("neutro")
    played = tab.play_rps(game.ROCK)  # pedra quebra tesoura: o pet perde
    assert played.result == game.LOST
    assert tab.face.shown == "bravo"
    assert "você ganhou" in tab.result.text()
    assert "Pulso 0 × 1 você" in tab.score.text()
    tab.face.advance(7.0)  # passou a reação de 6 s
    assert tab.face.shown == "neutro"


def test_empate_nao_muda_a_cara_e_conta_empate(make_tab):
    tab = make_tab(game.ROCK)
    tab.face.set_mood("neutro")
    assert tab.play_rps(game.ROCK).result == game.DRAW
    assert tab.face.shown == "neutro"
    assert "1 empate" in tab.score.text()


def test_par_ou_impar_usa_o_lado_escolhido_e_mostra_a_soma(make_tab):
    tab = make_tab(3)  # o pet mostra 3 dedos
    tab.side_buttons[game.ODD].setChecked(True)
    played = tab.play_even_odd(2)  # 2 + 3 = 5, ímpar: o dono escolheu ímpar e ganha
    assert played.result == game.LOST
    assert "2 + Pulso 3 = 5" in tab.result.text()
    assert tab.face.shown == "bravo"


def test_botoes_jogam_de_verdade(make_tab):
    tab = make_tab(game.SCISSORS)
    tab.rps_buttons[game.ROCK].click()
    assert tab.face.shown == "bravo"
    tab.picker.setCurrentIndex(1)
    assert tab.pages.currentIndex() == 1
    tab.finger_buttons[4].click()
    assert "Hoje: Pulso" in tab.score.text()


def test_sem_placar_a_aba_funciona(qapp):
    tab = GameTab(None, FixedRng(game.ROCK))
    tab.show()
    tab.play_rps(game.ROCK)
    assert tab.score.text() == ""
    tab.close()
