import pytest

from pulso import __version__
from pulso.__main__ import main


def test_version_flag_imprime_a_versao(capsys):
    with pytest.raises(SystemExit) as saida:
        main(["--version"])
    assert saida.value.code == 0
    assert capsys.readouterr().out.strip() == f"pulso {__version__}"
