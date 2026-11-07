"""Interface offscreen: o clique chama `reward`, a pausa troca o selo e para o sensor."""

import random

import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.fake import ScriptedSensor
from pulso.storage.brain_store import AutoSaver
from pulso.ui import phrases
from pulso.ui.app import build_controller
from pulso.ui.main_window import MainWindow
from tests.test_controller import FRAME, SpyEngine, make_habits

MOODS = ("animado", "contente", "entediado", "sonolento", "preocupado")


def _controller(clock, path):
    engine, sensor = SpyEngine(), ScriptedSensor([FRAME])
    controller = PetController(
        sensor,
        clock,
        engine,
        MoodDecoder(engine.groups),
        RewardRules(clock),
        AutoSaver(engine, path, 1, clock),
        make_habits(clock),
    )
    return controller, sensor, engine


@pytest.fixture
def env(qapp, tmp_path):
    clock, path = FakeClock(), tmp_path / "cerebro.npz"
    controller, sensor, engine = _controller(clock, path)
    window = MainWindow(controller, clock, first_run=False, tick_ms=3_600_000, rng=random.Random(1))
    yield window, controller, sensor, engine, clock, path
    window.close()


def test_clique_em_carinho_chama_reward_e_nao_ha_bronca(env):
    window, _, _, engine, clock, _ = env
    window.pet_tab.care.click()
    assert engine.rewards == [1.0]
    assert not hasattr(window.pet_tab, "scold")  # a bronca saiu na etapa 7


def test_clique_da_retorno_visual_imediato(env):
    window, *_ = env
    assert not window.pet_tab.pet._bursts
    window.pet_tab.care.click()
    assert [e for e, _ in window.pet_tab.pet._bursts] == ["💚"]
    assert window.pet_tab.speech.text() == phrases.PETTED


def test_pausar_troca_o_selo_para_o_sensor_e_o_pet_dorme(env):
    window, controller, sensor, *_ = env
    tab = window.pet_tab
    assert tab.badge.isHidden()  # observando: sem aviso constante
    assert tab.pause.accessibleName() == "Pausar observação"
    assert tab.pause.text() == ""  # só o ícone
    window.tick()
    calls = sensor.calls
    tab.pause.click()
    assert "pausada" in tab.badge.text() and not tab.badge.isHidden()
    assert tab.pause.accessibleName() == "Retomar observação"
    assert phrases.MEANING_SLEEPING == tab.caption.text()
    assert tab.pet.sleeping
    assert tab.speech.text() == phrases.PAUSED
    assert not tab.care.isEnabled()
    for _ in range(5):
        window.tick()
    assert sensor.calls == calls  # nenhuma leitura enquanto pausado
    tab.pause.click()
    assert tab.badge.isHidden()
    assert not tab.pet.sleeping
    assert controller.paused is False


def test_pausar_grava_o_cerebro_e_fechar_tambem(env):
    window, _, _, _, _, path = env
    window.pet_tab.pause.click()
    assert path.exists()
    path.unlink()
    window.close()
    assert path.exists()


def test_o_laco_mantem_o_rosto_das_regras_e_a_fala(env):
    window, *_ = env
    for _ in range(10):
        window.tick()
    assert window.pet_tab.pet.target == window._controller.verdict.mood
    assert window.pet_tab.speech.text() != ""


def test_boas_vindas_no_primeiro_uso_ficam_ate_o_dono_agir(qapp, tmp_path):
    clock = FakeClock()
    controller, _, _ = _controller(clock, tmp_path / "c.npz")
    window = MainWindow(controller, clock, first_run=True, tick_ms=3_600_000)
    assert window.pet_tab.speech.text() == phrases.WELCOME
    for _ in range(12):  # a rede decide um humor, mas a fala de boas-vindas continua
        window.tick()
        clock.advance(1)
    assert window.pet_tab.speech.text() == phrases.WELCOME
    window.pet_tab.care.click()
    assert window.pet_tab.speech.text() == phrases.PETTED
    window.close()


# ---- primeiro uso e arquivo ruim ---------------------------------------------------------------


def test_primeiro_uso_cria_o_cerebro_e_o_segundo_uso_nao_e_primeiro(tmp_path):
    clock, path = FakeClock(), tmp_path / "pasta" / "cerebro.npz"
    _, first = build_controller(ScriptedSensor([FRAME]), clock, path)
    assert first and path.exists()
    _, again = build_controller(ScriptedSensor([FRAME]), clock, path)
    assert not again


def test_arquivo_ruim_avisa_e_nao_e_apagado(tmp_path):
    path = tmp_path / "cerebro.npz"
    path.write_bytes(b"isto nao e um npz")
    avisos = []
    _, first = build_controller(ScriptedSensor([FRAME]), FakeClock(), path, avisos.append)
    assert len(avisos) == 1 and "novo" in avisos[0]
    guardados = list(tmp_path.glob("cerebro.recusado-*.npz"))
    assert len(guardados) == 1 and guardados[0].read_bytes() == b"isto nao e um npz"
    assert path.exists() and not first  # há um cérebro novo no lugar


def test_rosto_explica_o_humor_embaixo(env):
    window, *_ = env
    tab = window.pet_tab
    assert tab.caption.text() == phrases.mood_meaning(window._controller.verdict)
    for _ in range(10):
        window.tick()
    assert tab.pet.target == "neutro"
    assert "nada pendente" in tab.caption.text()
    assert phrases.MEANING_HINT in tab.pet.toolTip()


def test_nenhum_texto_usa_o_emoji_de_olho(env):
    window, *_ = env
    tab = window.pet_tab
    textos = [tab.pause.toolTip(), tab.badge.text(), tab.care.text()]
    textos += [phrases.WELCOME, phrases.PAUSED, phrases.MEANING_HINT]
    assert not any("👁" in t for t in textos)


def test_carinho_deixa_o_rosto_contente_e_depois_volta_ao_humor(env):
    window, *_ = env
    pet = window.pet_tab.pet
    pet.set_mood("preocupado")
    window.pet_tab.care.click()
    assert pet.shown == "contente" and pet.target == "preocupado"
    for _ in range(60):  # ~3 s
        pet.advance(0.05)
    assert pet.shown == "preocupado"
    window.pet_tab.pause.click()  # nada preso: dormindo, o rosto assenta
    window.pet_tab.pause.click()


def test_abre_no_menor_tamanho_e_o_texto_nao_e_cortado(qapp, tmp_path):
    clock = FakeClock()
    controller, _, _ = _controller(clock, tmp_path / "c.npz")
    window = MainWindow(controller, clock, first_run=True, tick_ms=3_600_000)
    window.show()
    qapp.processEvents()
    assert window.size() == window.minimumSize()  # abre no mínimo
    tab = window.pet_tab
    for label in (tab.speech, tab.caption):  # a altura reservada comporta o texto quebrado
        assert label.heightForWidth(label.width()) <= label.height()
    assert tab.pet.height() >= tab.pet.minimumHeight()
    window.close()


def test_pausa_fica_no_topo_ao_lado_da_pilula_so_com_icone(env, qapp):
    window, *_ = env
    tab = window.pet_tab
    window.show()
    qapp.processEvents()
    assert tab.pause.text() == "" and not tab.pause.icon().isNull()
    assert abs(tab.pause.geometry().center().y() - tab.mode_button.geometry().center().y()) <= 4
    assert tab.pause.x() > tab.mode_button.x()  # depois da pílula de modo


def test_barra_de_abas_aparece_com_o_cerebro_e_o_titulo_continua_pulso(env, qapp):
    window, *_ = env
    window.show()
    qapp.processEvents()
    tabs = window.tabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Pulso", "Jogo", "Cérebro"]
    assert tabs.tabBar().isVisible()
    assert window.windowTitle() == "Pulso"


def test_build_controller_leva_o_modo_e_o_sensor_de_reuniao(tmp_path):
    from pulso.habits.focus_cycle import Mode, Phase
    from pulso.sensors.meeting import FakeMeetingSensor
    from pulso.storage.config import Settings

    controller, _ = build_controller(
        ScriptedSensor([FRAME]),
        FakeClock(),
        tmp_path / "cerebro.npz",
        db=":memory:",
        settings=Settings(mode="casual"),
        meeting=FakeMeetingSensor([True]),
    )
    assert controller.habits.mode is Mode.CASUAL
    assert controller.habits.cycle.phase is Phase.OFF
