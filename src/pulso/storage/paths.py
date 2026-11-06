"""Onde o Pulso guarda seus arquivos.

Por padrão, a pasta de dados do usuário do Windows (`%LOCALAPPDATA%\\Pulso`). A variável de ambiente
`PULSO_DATA_DIR` troca a pasta: os testes e as demonstrações a usam para **nunca** tocar nos dados
reais do dono (TRD §6).
"""

import os
from pathlib import Path

from platformdirs import user_data_dir

ENV_DATA_DIR = "PULSO_DATA_DIR"
BRAIN_FILE = "cerebro.npz"
DB_FILE = "pulso.db"


def data_dir() -> Path:
    """Pasta de dados. Não é criada aqui: quem grava cria (`mkdir(parents=True, exist_ok=True)`)."""
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        return Path(override)
    return Path(user_data_dir("Pulso", appauthor=False))


def brain_path() -> Path:
    return data_dir() / BRAIN_FILE
