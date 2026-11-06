"""O rosto: transição suave, microanimações e o relógio de quadros que descansa."""

import random

import pytest

from pulso.ui.pet_widget import LOOKS, PetWidget
from pulso.ui.phrases import SLEEPING


@pytest.fixture
def pet(qapp):
    w = PetWidget(rng=random.Random(3))
    w.resize(400, 320)
    yield w
    w.close()


def test_troca_de_humor_e_suave_e_chega_ao_alvo(pet):
    pet.set_mood("contente")
    pet.advance(0.05)
    assert 0.0 < pet._look["happy"] < 1.0  # no meio do caminho, não pulou
    for _ in range(40):
        pet.advance(0.033)
    assert pet._look["happy"] == pytest.approx(1.0, abs=0.01)


def test_todos_os_humores_desenham_sem_erro(pet):
    pet.show()
    for name in LOOKS:
        pet.set_mood(name)
        for _ in range(15):
            pet.advance(0.1)
        assert not pet.grab().isNull()


def test_humor_desconhecido_e_recusado(pet):
    with pytest.raises(ValueError):
        pet.set_mood("furioso")


def test_pet_pisca_a_cada_3_a_6_segundos(pet):
    pet.set_mood("contente")
    piscou = []
    for _ in range(600):  # 20 s
        pet.advance(1 / 30)
        piscou.append(pet._blink_factor() < 0.5)
    inicios = [i for i in range(1, len(piscou)) if piscou[i] and not piscou[i - 1]]
    assert 3 <= len(inicios) <= 7
    intervalos = [(b - a) / 30 for a, b in zip(inicios, inicios[1:], strict=False)]
    assert all(2.5 <= x <= 6.5 for x in intervalos)


def test_dormindo_nao_pisca_e_o_relogio_de_quadros_descansa(pet):
    pet.show()
    pet.set_mood(SLEEPING)
    assert pet.animating
    for _ in range(100):
        pet.advance(0.05)
        assert pet._blink_factor() == 1.0
    assert pet.settled()
    pet._on_timer()  # o próprio relógio percebe que nada mais se mexe...
    assert not pet.animating  # ...e para
    pet.set_mood("animado")  # acordou: volta a animar
    assert pet.animating


def test_janela_oculta_nao_anima(pet):
    pet.show()
    assert pet.animating
    pet.hide()
    assert not pet.animating
