"""Contraste mínimo de 4.5:1 (WCAG AA) para os textos das duas paletas (Design Brief §3)."""

import pytest

from pulso.ui.theme import DARK, FACE_BACKGROUND, LIGHT, MOOD_COLORS, contrast


def test_formula_de_contraste_conhece_os_extremos():
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast("#777777", "#777777") == pytest.approx(1.0)


@pytest.mark.parametrize("palette", [LIGHT, DARK], ids=["claro", "escuro"])
def test_textos_tem_contraste_aa(palette):
    pares = [
        (palette.text, palette.background),
        (palette.text, palette.surface),
        (palette.text_secondary, palette.background),
        (palette.text_secondary, palette.surface),
        (palette.on_primary, palette.primary),
        (palette.success, palette.surface),
        (palette.warning, palette.surface),
        (palette.error, palette.surface),
    ]
    for fg, bg in pares:
        assert contrast(fg, bg) >= 4.5, (fg, bg)


def test_cores_dos_humores_se_destacam_do_fundo_do_rosto():
    # Não é texto, mas carrega o humor: pede-se ao menos 3:1 (WCAG para elementos gráficos).
    for mood, color in MOOD_COLORS.items():
        assert contrast(color, FACE_BACKGROUND) >= 3.0, mood
