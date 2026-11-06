import pytest

from pulso.clock import FakeClock
from pulso.loop import SensorLoop
from pulso.sensors.base import SensorFrame
from pulso.sensors.fake import ScriptedSensor

FRAME = SensorFrame(10.0, 40.0, 14.5, 3.0, "codigo", 2)


def make_loop(script):
    sensor = ScriptedSensor(script)
    return sensor, SensorLoop(sensor, FakeClock())


def test_tick_returns_sensor_reading():
    sensor, loop = make_loop([FRAME])
    assert loop.tick() == FRAME
    assert sensor.calls == 1


def test_paused_sensor_gets_zero_calls():
    sensor, loop = make_loop([FRAME])
    loop.pause()
    for _ in range(50):
        assert loop.tick() is None
    assert sensor.calls == 0


def test_run_while_paused_never_reads():
    sensor, loop = make_loop([FRAME])
    loop.pause()
    received = []
    loop.run(received.append, max_ticks=5)
    assert received == []
    assert sensor.calls == 0


def test_resume_reads_again():
    sensor, loop = make_loop([FRAME])
    loop.pause()
    loop.tick()
    loop.resume()
    assert loop.tick() == FRAME
    assert sensor.calls == 1


def test_sensor_error_becomes_unknown_reading():
    _, loop = make_loop([RuntimeError("falhou"), FRAME])
    frame = loop.tick()
    assert frame is not None
    assert frame.valid is False
    assert frame.category == "outro"
    assert loop.tick() == FRAME  # o laço segue vivo


def test_error_message_not_logged(caplog):
    _, loop = make_loop([RuntimeError("segredo-do-sensor")])
    with caplog.at_level("WARNING"):
        loop.tick()
    assert "segredo-do-sensor" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_run_advances_fake_clock():
    clock = FakeClock()
    loop = SensorLoop(ScriptedSensor([FRAME]), clock, interval=1.0)
    received = []
    loop.run(received.append, max_ticks=3)
    assert len(received) == 3
    assert clock.now() == 3.0


def test_empty_script_rejected():
    with pytest.raises(ValueError):
        ScriptedSensor([])
