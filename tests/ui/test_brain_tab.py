"""Aba Cérebro: desenha a rede, congela, não gasta nada escondida e a janela acompanha a aba."""

import random

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QEvent

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
from pulso.storage.brain_store import AutoSaver
from pulso.ui.brain_tab import BRAIN_PREFERRED, HELP, SOURCE_COLORS, BrainTab, HelpButton
from pulso.ui.main_window import MainWindow
from pulso.ui.theme import MOOD_COLORS
from tests.test_controller import FRAME, SpyEngine, make_habits


@pytest.fixture
def parts(qapp, tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    controller = PetController(
        ScriptedSensor([FRAME]),
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, tmp_path / "c.npz", 1, clock),
        make_habits(clock),
    )
    window = MainWindow(controller, clock, tick_ms=3_600_000, rng=random.Random(1))
    yield window, controller, clock
    window.close()


def _show(window, qapp, brain=True):
    window.show()
    if brain:
        window.tabs.setCurrentWidget(window.brain_tab)
    qapp.processEvents()


def _points(tab, key):
    return len(tab._scatters[key].getData()[0])


def _count_snapshots(controller):
    """Conta quantas vezes a aba pediu a fotografia da rede."""
    calls = []
    original = controller.snapshot
    controller.snapshot = lambda: (calls.append(1), original())[1]
    return calls


def test_desenha_os_pulsos_de_cada_camada_com_a_cor_do_humor(parts, qapp):
    window, controller, _ = parts
    _show(window, qapp)
    for _ in range(5):
        window.tick()
    tab = window.brain_tab
    assert _points(tab, "entrada") > 0 and _points(tab, "oculta_exc") > 0
    assert sum(_points(tab, m) for m in MOOD_COLORS if m != "dormindo") > 0
    saida = tab._scatters["animado"].opts["brush"].color().name().upper()
    assert saida == MOOD_COLORS["animado"].upper()  # a cor do grupo é a do humor
    x = tab._scatters["entrada"].getData()[0]
    assert x.min() >= -2.0 and x.max() <= 0.0  # tempo de rede, 0 = agora


def test_potenciais_tem_tres_tracos_do_tamanho_do_raster(parts, qapp):
    window, *_ = parts
    _show(window, qapp)
    window.tick()
    tab = window.brain_tab
    tamanhos = {len(line.getData()[0]) for line in tab._v_lines}
    # 1 volta = 100 ms de rede; o gráfico guarda no máximo 500
    assert len(tab._v_lines) == 3 and tamanhos == {100}


def test_dopamina_mostra_o_valor_e_a_cor_de_quem_deu(parts, qapp):
    window, controller, clock = parts
    _show(window, qapp)
    window.pet_tab.care.click()
    clock.advance(30)
    window.pet_tab.scold.click()
    window.brain_tab.refresh()
    opts = window.brain_tab._dopamine_bars.opts
    assert opts["height"][0] > 0 > opts["height"][1]
    assert opts["x"][0] == pytest.approx(-0.5) and opts["x"][1] == pytest.approx(0.0)
    assert opts["brushes"][0].color().name().upper() == SOURCE_COLORS["dono"].upper()


def test_dopamina_antiga_sai_do_grafico(parts, qapp):
    window, controller, clock = parts
    _show(window, qapp)
    window.pet_tab.care.click()
    clock.advance(601)  # passou dos 10 min
    window.brain_tab.refresh()
    assert len(window.brain_tab._dopamine_bars.opts["height"]) == 0


def test_barras_de_humor_batem_com_a_contagem_do_decodificador(parts, qapp):
    window, controller, _ = parts
    _show(window, qapp)
    for _ in range(12):
        window.tick()
    barras = window.brain_tab._mood_bars.opts["width"]
    assert np.array_equal(barras, controller.mood_counts())


def test_mapa_de_pesos_e_o_modo_so_o_que_mudou(parts, qapp):
    window, controller, clock = parts
    _show(window, qapp)
    tab = window.brain_tab
    for _ in range(3):
        window.tick()
    pesos = tab._weights_image.image
    assert pesos.shape == controller.snapshot().weights.shape
    tab.only_changes.setChecked(True)
    assert not tab._weights_image.image.any()  # nada aprendeu ainda: diferença zero
    window.pet_tab.care.click()
    clock.advance(30)
    window.pet_tab.care.click()
    tab.refresh()
    assert tab._weights_image.image.any()  # a recompensa mexeu em alguma sinapse
    tab.only_changes.setChecked(False)
    assert np.array_equal(tab._weights_image.image, controller.snapshot().weights)


def test_rodape_mostra_custo_do_passo_e_recompensas(parts, qapp):
    window, _, clock = parts
    _show(window, qapp)
    window.tick()
    window.pet_tab.care.click()
    window.brain_tab.refresh()
    texto = window.brain_tab.footer.text()
    assert "ms por volta" in texto and "+1 / −0" in texto


# ---- custo zero escondida, congelar -----------------------------------------------------------


def test_aba_escondida_nao_redesenha_nem_pede_a_fotografia(parts, qapp):
    window, controller, _ = parts
    _show(window, qapp, brain=False)  # janela visível, mas na aba Pet
    tab = window.brain_tab
    assert not tab.isVisible()
    antes, calls = tab.refresh_count, _count_snapshots(controller)
    for _ in range(5):
        window.tick()
    assert tab.refresh_count == antes and not calls


def test_janela_minimizada_ou_escondida_nao_redesenha(parts, qapp):
    window, controller, _ = parts
    _show(window, qapp)
    window.tick()
    window.hide()  # o mesmo efeito, para a aba, de minimizar a janela
    qapp.processEvents()
    antes, calls = window.brain_tab.refresh_count, _count_snapshots(controller)
    for _ in range(5):
        window.tick()
    assert window.brain_tab.refresh_count == antes and not calls


def test_ao_voltar_para_a_aba_ela_se_poe_em_dia(parts, qapp):
    window, *_ = parts
    _show(window, qapp, brain=False)
    for _ in range(3):
        window.tick()
    antes = window.brain_tab.refresh_count
    window.tabs.setCurrentWidget(window.brain_tab)
    assert window.brain_tab.refresh_count > antes
    assert _points(window.brain_tab, "entrada") > 0


def test_congelar_para_os_graficos_e_continuar_retoma(parts, qapp):
    window, *_ = parts
    _show(window, qapp)
    tab = window.brain_tab
    window.tick()
    tab.freeze.click()
    assert tab.frozen and tab.freeze.text() == "Continuar"
    parado = tab.refresh_count
    antes = tab._v_lines[0].getData()[0].copy()
    for _ in range(3):
        window.tick()
    assert tab.refresh_count == parado
    assert np.array_equal(tab._v_lines[0].getData()[0], antes)
    tab.freeze.click()
    assert not tab.frozen and tab.refresh_count > parado
    assert len(tab._v_lines[0].getData()[0]) > len(antes)  # a rede seguiu rodando por baixo


def test_pausa_de_privacidade_nao_alimenta_os_graficos(parts, qapp):
    window, controller, _ = parts
    _show(window, qapp)
    window.tick()
    window.pet_tab.pause.click()
    calls = _count_snapshots(controller)
    for _ in range(3):
        window.tick()
    assert not calls  # pausado: o laço nem chega a atualizar a aba


# ---- ajuda, janela e teclado ------------------------------------------------------------------


def test_cada_grafico_tem_um_botao_de_ajuda_com_texto(parts, qapp):
    window, *_ = parts
    botoes = window.brain_tab.findChildren(HelpButton)
    assert len(botoes) == 5 == len(HELP)
    assert {b.help_text for b in botoes} == set(HELP.values())
    assert all(
        b.toolTip() == b.help_text and b.accessibleName().startswith("Ajuda") for b in botoes
    )


def test_a_janela_cresce_ao_abrir_o_cerebro_e_volta_ao_tamanho_do_pet(parts, qapp):
    window, *_ = parts
    window.show()
    qapp.processEvents()
    pet = window.size()
    window.tabs.setCurrentWidget(window.brain_tab)
    qapp.processEvents()
    assert window.width() >= BRAIN_PREFERRED.width() and window.height() >= BRAIN_PREFERRED.height()
    window.tabs.setCurrentWidget(window.pet_tab)
    qapp.processEvents()
    assert window.size() == pet
    assert window.minimumSize() == window._pet_minimum  # e o pet segue abrindo compacto


def test_ctrl_1_e_ctrl_2_trocam_de_aba(parts, qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window, *_ = parts
    window.show()
    qapp.processEvents()
    QTest.keyClick(window, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget() is window.brain_tab
    QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget() is window.pet_tab


def test_tab_isolada_cria_sem_janela(parts, qapp):
    _, controller, clock = parts
    tab = BrainTab(controller, clock)
    assert tab.refresh_count == 1  # o desenho inicial, mesmo antes de aparecer
    tab.close()
    tab.deleteLater()  # uma aba solta (sem janela) precisa ser apagada, senão o Qt cai ao sair
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
