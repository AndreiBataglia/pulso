"""O controlador sem Qt: laço de 1 s, recompensas do dono, pausa e gravação."""

import numpy as np
import pytest

from pulso.brain.decoding import MoodDecoder
from pulso.brain.numpy_engine import NumpyEngine
from pulso.brain.rewards import RewardRules
from pulso.clock import FakeClock
from pulso.controller import PetController
from pulso.sensors.base import SensorFrame
from pulso.sensors.fake import ScriptedSensor
from pulso.storage.brain_store import AutoSaver

FRAME = SensorFrame(40.0, 50.0, 10.0, 0.0, "codigo", 2)


class SpyEngine(NumpyEngine):
    """Motor de verdade que anota as recompensas recebidas."""

    def __init__(self) -> None:
        super().__init__(seed=1)
        self.rewards: list[float] = []

    def reward(self, value: float) -> None:
        self.rewards.append(value)
        super().reward(value)


@pytest.fixture
def parts(tmp_path):
    clock = FakeClock()
    sensor = ScriptedSensor([FRAME])
    engine = SpyEngine()
    path = tmp_path / "cerebro.npz"
    saver = AutoSaver(engine, path, seed=1, clock=clock)
    controller = PetController(
        sensor, clock, engine, MoodDecoder(engine.groups), RewardRules(clock), saver
    )
    return controller, sensor, engine, clock, path


def test_tick_le_o_sensor_e_decide_o_humor_a_cada_10_voltas(parts):
    controller, sensor, _, clock, _ = parts
    results = []
    for _ in range(10):
        results.append(controller.tick())
        clock.advance(1)
    assert sensor.calls == 10
    assert all(r is not None for r in results)
    assert controller.mood in ("animado", "contente", "entediado", "sonolento", "preocupado")
    assert results[-1].mood == controller.mood


def test_carinho_e_bronca_chamam_reward_com_o_sinal_certo(parts):
    controller, _, engine, clock, _ = parts
    assert controller.owner_reward(+1) is True
    clock.advance(10)
    assert controller.owner_reward(-1) is True
    assert engine.rewards == [1.0, -1.0]


def test_clique_repetido_e_ignorado(parts):
    controller, _, engine, clock, _ = parts
    assert controller.owner_reward(+1) is True
    clock.advance(1)
    assert controller.owner_reward(+1) is False
    assert engine.rewards == [1.0]


def test_pausa_nao_le_sensor_nao_simula_e_nao_recompensa(parts):
    controller, sensor, engine, clock, _ = parts
    controller.tick()
    before = {k: v.copy() for k, v in engine.state_dict().items()}
    calls = sensor.calls
    controller.pause()
    for _ in range(30):
        assert controller.tick() is None
        clock.advance(1)
    assert controller.owner_reward(+1) is False
    assert sensor.calls == calls  # o sensor nem foi chamado
    assert engine.rewards == []
    after = engine.state_dict()
    assert all(np.array_equal(before[k], after[k]) for k in before)  # a rede não aprendeu nada
    controller.resume()
    assert controller.tick() is not None
    assert sensor.calls == calls + 1


def test_pausar_e_sair_gravam_o_cerebro(parts):
    controller, _, _, _, path = parts
    assert not path.exists()
    controller.pause()
    assert path.exists()
    path.unlink()
    controller.shutdown()
    assert path.exists()


def test_autosave_a_cada_5_minutos_no_laco(parts):
    controller, _, _, clock, path = parts
    controller.tick()
    assert not path.exists()
    clock.advance(301)
    controller.tick()
    assert path.exists()


def test_leitura_invalida_nao_derruba_o_laco(tmp_path):
    clock = FakeClock()
    engine = SpyEngine()
    sensor = ScriptedSensor([RuntimeError("falhou"), FRAME])
    saver = AutoSaver(engine, tmp_path / "c.npz", 1, clock)
    controller = PetController(
        sensor, clock, engine, MoodDecoder(engine.groups), RewardRules(clock), saver
    )
    assert controller.tick() is not None  # leitura "desconhecida", sem exceção
    assert controller.tick() is not None
