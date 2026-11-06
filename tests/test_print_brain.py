from pulso.__main__ import main


def test_print_brain_with_fake_sensors_prints_a_mood_every_10_seconds(capsys):
    assert main(["--print-brain", "--fake-sensors", "--max-seconds", "40"]) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if "humor:" in line]
    assert len(lines) == 4


def test_print_brain_never_prints_sensor_values(capsys):
    main(["--print-brain", "--fake-sensors", "--max-seconds", "20"])
    out = capsys.readouterr().out
    # Nem a categoria do programa nem números de CPU/RAM aparecem: só o humor.
    assert "codigo" not in out and "cpu" not in out.lower()


def test_fake_sensors_stop_by_themselves_at_the_end_of_the_script(capsys):
    assert main(["--print-brain", "--fake-sensors"]) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if "humor:" in line]
    assert len(lines) == 24  # 240 s de roteiro / 10 s
