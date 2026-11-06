"""Salvar/carregar o cérebro. Sempre em pasta temporária: nunca toca nos dados reais do dono."""

import numpy as np
import pytest

from pulso.brain.numpy_engine import NumpyEngine
from pulso.clock import FakeClock
from pulso.storage import brain_store as bs
from pulso.storage import paths


def trained_engine(seed: int = 1) -> NumpyEngine:
    """Um cérebro que já mexeu nos pesos: roda, recebe uma recompensa e roda mais."""
    engine = NumpyEngine(seed=seed)
    rates = np.full(engine.n_inputs, 60.0)
    engine.step(rates, 300)
    engine.reward(1.0)
    return engine


def test_save_then_load_gives_the_same_weights(tmp_path):
    original = trained_engine()
    path = tmp_path / "cerebro.npz"
    bs.save_brain(original, path, seed=1)

    restored = NumpyEngine(seed=99)  # outra semente: os pesos têm que vir do arquivo
    bs.load_brain(restored, path)

    a, b = original.state_dict(), restored.state_dict()
    assert a.keys() == b.keys()
    for key in a:
        assert np.array_equal(a[key], b[key]), key


def test_the_seed_is_saved_and_returned(tmp_path):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(NumpyEngine(seed=5), path, seed=5)
    assert bs.load_brain(NumpyEngine(seed=0), path) == 5


def test_unknown_version_is_refused_and_leaves_the_engine_untouched(tmp_path, caplog):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files}
    arrays["format_version"] = np.array(999)
    np.savez(path, **arrays)

    engine = NumpyEngine(seed=2)
    before = engine.state_dict()
    with caplog.at_level("WARNING"), pytest.raises(bs.BrainFileError):
        bs.load_brain(engine, path)
    assert "desconhecida" in caplog.text  # avisou no log
    for key, value in engine.state_dict().items():
        assert np.array_equal(before[key], value)


def test_a_file_from_another_engine_is_refused(tmp_path):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files}
    arrays["engine"] = np.array("outro_motor")
    np.savez(path, **arrays)
    with pytest.raises(bs.BrainFileError):
        bs.load_brain(NumpyEngine(seed=1), path)


def test_a_file_with_different_moods_is_refused(tmp_path):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files}
    arrays["groups"] = np.array(["a", "b", "c", "d", "e"])
    np.savez(path, **arrays)
    with pytest.raises(bs.BrainFileError):
        bs.load_brain(NumpyEngine(seed=1), path)


def test_a_corrupted_file_is_refused_not_a_crash(tmp_path):
    path = tmp_path / "cerebro.npz"
    path.write_bytes(b"isto nao e um npz")
    with pytest.raises(bs.BrainFileError):
        bs.load_brain(NumpyEngine(seed=1), path)


def test_the_file_never_holds_pickled_objects(tmp_path):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    with np.load(path, allow_pickle=False) as data:  # se houvesse objeto, isto levantaria erro
        for key in data.files:
            data[key]


def test_saving_is_atomic_and_leaves_no_tmp_file(tmp_path):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    assert [p.name for p in tmp_path.iterdir()] == ["cerebro.npz"]


def test_a_failed_save_keeps_the_old_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    old = path.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(bs.np, "savez", boom)
    with pytest.raises(OSError):
        bs.save_brain(trained_engine(2), path, seed=2)
    assert path.read_bytes() == old
    assert [p.name for p in tmp_path.iterdir()] == ["cerebro.npz"]


def test_save_creates_the_folder(tmp_path):
    path = tmp_path / "a" / "b" / "cerebro.npz"
    bs.save_brain(trained_engine(), path, seed=1)
    assert path.exists()


def test_load_or_create_without_a_file_makes_a_new_brain(tmp_path):
    engine, seed = bs.load_or_create(tmp_path / "cerebro.npz")
    assert isinstance(seed, int)
    assert engine.groups


def test_load_or_create_reopens_what_was_learned(tmp_path):
    path = tmp_path / "cerebro.npz"
    original = trained_engine(seed=3)
    bs.save_brain(original, path, seed=3)
    engine, seed = bs.load_or_create(path)
    assert seed == 3
    assert np.array_equal(
        engine.state_dict()["w_hidden_out"], original.state_dict()["w_hidden_out"]
    )


def test_load_or_create_does_not_swallow_a_bad_file(tmp_path):
    path = tmp_path / "cerebro.npz"
    path.write_bytes(b"lixo")
    with pytest.raises(bs.BrainFileError):
        bs.load_or_create(path)
    assert path.read_bytes() == b"lixo"  # não apaga nem sobrescreve por conta própria


# ---- salvamento automático -------------------------------------------------------------------


def make_saver(tmp_path, clock):
    return bs.AutoSaver(trained_engine(), tmp_path / "cerebro.npz", seed=1, clock=clock)


def test_autosave_waits_for_the_interval(tmp_path):
    clock = FakeClock()
    saver = make_saver(tmp_path, clock)
    clock.advance(299)
    assert saver.tick() is False
    assert not (tmp_path / "cerebro.npz").exists()
    clock.advance(2)
    assert saver.tick() is True
    assert (tmp_path / "cerebro.npz").exists()


def test_autosave_repeats_every_interval(tmp_path):
    clock = FakeClock()
    saver = make_saver(tmp_path, clock)
    clock.advance(301)
    assert saver.tick() is True
    clock.advance(10)
    assert saver.tick() is False
    clock.advance(300)
    assert saver.tick() is True


def test_flush_saves_right_away(tmp_path):
    saver = make_saver(tmp_path, FakeClock())
    saver.flush()  # como ao pausar ou ao sair
    assert (tmp_path / "cerebro.npz").exists()


def test_a_disk_error_does_not_crash_the_loop(tmp_path):
    blocker = tmp_path / "ocupado"
    blocker.write_text("sou um arquivo, não uma pasta")
    clock = FakeClock()
    saver = bs.AutoSaver(trained_engine(), blocker / "cerebro.npz", seed=1, clock=clock)
    saver.flush()  # não levanta


# ---- pastas ----------------------------------------------------------------------------------


def test_data_dir_follows_the_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(tmp_path))
    assert paths.data_dir() == tmp_path
    assert paths.brain_path() == tmp_path / "cerebro.npz"


def test_default_data_dir_is_a_pulso_folder(monkeypatch):
    monkeypatch.delenv(paths.ENV_DATA_DIR, raising=False)
    assert paths.data_dir().name == "Pulso"
