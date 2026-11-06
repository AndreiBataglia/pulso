"""Guarda de privacidade: o código-fonte nunca pode ler o título da janela nem as teclas."""

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"

# Montadas por partes para este arquivo (que fica fora de src/) também não as conter por inteiro.
FORBIDDEN = [
    "GetWindow" + "Text",  # título da janela (A, W e Length)
    "GetAsync" + "KeyState",  # sondar teclas
    "SetWindows" + "HookEx",  # hook global de teclado
    "pyn" + "put",
    "keyboard" + " import",
    "import " + "keyboard",
]


def test_src_has_no_forbidden_apis():
    files = list(SRC.rglob("*.py"))
    assert files, "src/ não encontrado: o teste estaria passando no vazio"
    hits = [
        f"{path.relative_to(SRC)}: {word}"
        for path in files
        for word in FORBIDDEN
        if word in path.read_text(encoding="utf-8")
    ]
    assert hits == []
