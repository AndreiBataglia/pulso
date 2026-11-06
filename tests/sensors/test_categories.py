from pulso.sensors.categories import categorize


def test_known_process():
    assert categorize("code.exe") == "codigo"
    assert categorize("chrome.exe") == "navegador"


def test_case_insensitive():
    assert categorize("Code.EXE") == "codigo"


def test_unknown_process_falls_to_other():
    assert categorize("programa_que_nao_existe.exe") == "outro"


def test_empty_or_none_falls_to_other():
    assert categorize(None) == "outro"
    assert categorize("") == "outro"


def test_extra_table_overrides_builtin_and_adds_new():
    extra = {"Chrome.exe": "video", "meujogo.exe": "jogo"}
    assert categorize("chrome.exe", extra) == "video"
    assert categorize("meujogo.exe", extra) == "jogo"
    assert categorize("code.exe", extra) == "codigo"
