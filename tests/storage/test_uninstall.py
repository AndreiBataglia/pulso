"""Remover o Pulso: só com pastas temporárias e um registro falso, nunca com os dados do dono."""

import zipfile
from pathlib import Path

import pytest

from pulso.storage import uninstall


class FakeAutostart:
    def __init__(self, on: bool = True, fail: bool = False) -> None:
        self.on, self.fail = on, fail

    def enabled(self) -> bool:
        return self.on

    def set_enabled(self, on: bool) -> None:
        if self.fail:
            raise PermissionError
        self.on = on


@pytest.fixture
def folder(tmp_path) -> Path:
    path = tmp_path / "Pulso"
    path.mkdir()
    for name in ("cerebro.npz", "pulso.db", "pulso.db-wal", "config.toml", "pulso.ico",
                 "cerebro.recusado-20261107-120000.npz"):  # fmt: skip
        (path / name).write_bytes(b"x")
    return path


def test_apaga_so_os_arquivos_do_pulso_e_remove_a_pasta_vazia(folder):
    report = uninstall.remove_all(folder)
    assert report.ok and report.folder_removed and not folder.exists()
    assert "cerebro.npz" in report.removed and "pulso.db" in report.removed


def test_nao_apaga_o_que_nao_e_do_pulso_e_avisa(folder):
    (folder / "minhas-anotacoes.txt").write_text("importante")
    report = uninstall.remove_all(folder)
    assert (folder / "minhas-anotacoes.txt").exists()
    assert not report.folder_removed and "minhas-anotacoes.txt" in report.folder_kept_reason
    assert not (folder / "cerebro.npz").exists()


def test_tira_o_inicio_com_o_windows_e_o_atalho(folder, tmp_path):
    shortcut = tmp_path / "Pulso.lnk"
    shortcut.write_bytes(b"lnk")
    autostart = FakeAutostart(on=True)
    report = uninstall.remove_all(folder, autostart, shortcut)
    assert not autostart.on and not shortcut.exists()
    assert "Iniciar com o Windows" in report.removed and "atalho do Menu Iniciar" in report.removed


def test_atalho_com_outro_nome_nunca_e_apagado(folder, tmp_path):
    other = tmp_path / "Outro.lnk"
    other.write_bytes(b"lnk")
    uninstall.remove_all(folder, None, other)
    assert other.exists()


def test_uma_falha_nao_interrompe_o_resto(folder, tmp_path):
    shortcut = tmp_path / "Pulso.lnk"
    shortcut.write_bytes(b"lnk")
    report = uninstall.remove_all(folder, FakeAutostart(fail=True), shortcut)
    assert not report.ok and report.failed[0][0] == "Iniciar com o Windows"
    assert not shortcut.exists() and not (folder / "cerebro.npz").exists()


def test_pasta_inexistente_ou_ja_limpa_nao_da_erro(tmp_path):
    report = uninstall.remove_all(tmp_path / "Pulso")
    assert report.ok and report.removed == []


@pytest.mark.parametrize("bad", [Path.home(), Path(Path.home().anchor), Path.home().parent])
def test_recusa_pastas_perigosas(bad):
    with pytest.raises(uninstall.UnsafeFolderError):
        uninstall.remove_all(bad)


def test_recusa_pasta_qualquer_sem_cara_de_pulso(tmp_path):
    other = tmp_path / "Documentos"
    other.mkdir()
    (other / "cerebro.npz.txt").write_text("não é do Pulso")
    with pytest.raises(uninstall.UnsafeFolderError):
        uninstall.remove_all(other)
    assert (other / "cerebro.npz.txt").exists()


def test_pasta_com_outro_nome_mas_com_o_cerebro_dentro_vale(tmp_path):
    custom = tmp_path / "dados-do-teste"  # como o PULSO_DATA_DIR
    custom.mkdir()
    (custom / "cerebro.npz").write_bytes(b"x")
    assert uninstall.remove_all(custom).folder_removed


def test_backup_guarda_so_os_arquivos_do_pulso_e_nao_apaga_nada(folder, tmp_path):
    (folder / "minhas-anotacoes.txt").write_text("fora do backup")
    zip_path = uninstall.backup(folder, tmp_path / "bkp")
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "cerebro.npz" in names and "minhas-anotacoes.txt" not in names
    assert (folder / "cerebro.npz").exists()


def test_descreve_o_que_sera_apagado(folder, tmp_path):
    lines = "\n".join(uninstall.describe(folder, FakeAutostart(on=True), tmp_path / "Pulso.lnk"))
    assert "cerebro.npz" in lines and "Iniciar com o Windows" in lines
    assert "Atalho" not in lines  # o atalho não existe, então não é listado


def test_resumo_diz_como_tirar_o_programa(folder):
    assert uninstall.PIP_HINT in uninstall.summary(uninstall.remove_all(folder))
