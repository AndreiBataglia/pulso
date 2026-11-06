"""Ponto de entrada do comando `pulso`."""

import argparse

from pulso import __version__
from pulso.sensors.base import SensorFrame


def _format_frame(frame: SensorFrame) -> str:
    """Uma linha legível por leitura (só para desenvolvimento; nada é gravado)."""
    if not frame.valid:
        return "leitura desconhecida (o sensor falhou)"
    return (
        f"cpu {frame.cpu_percent:5.1f}%  ram {frame.ram_percent:5.1f}%  "
        f"hora {frame.hour_of_day:5.2f}  ocioso {frame.idle_seconds:6.1f}s  "
        f"categoria {frame.category:<10}  trocas/min {frame.app_switches_last_min}"
    )


def _print_sensors() -> None:
    # Importado aqui para o `--version` funcionar mesmo fora do Windows.
    from pulso.clock import SystemClock
    from pulso.loop import SensorLoop
    from pulso.sensors.windows import WindowsSensor

    clock = SystemClock()
    loop = SensorLoop(WindowsSensor(clock), clock)
    print("Lendo os sensores a cada 1 s. Ctrl+C para parar.")
    try:
        loop.run(lambda frame: print(_format_frame(frame), flush=True))
    except KeyboardInterrupt:
        print("\nParado.")


def _print_brain(fake_sensors: bool, max_seconds: int | None) -> None:
    """Roda sensores → codificador → rede → decodificador e imprime o humor a cada 10 s.

    Não imprime nada dos sensores (só o humor) e não grava nada em disco.
    """
    from pulso.brain.decoding import MoodDecoder
    from pulso.brain.encoding import encode
    from pulso.brain.numpy_engine import NumpyEngine
    from pulso.clock import FakeClock, SystemClock
    from pulso.loop import SensorLoop
    from pulso.sensors.fake import ScriptedSensor, demo_scenario

    if fake_sensors:
        clock = FakeClock()  # tempo falso: o roteiro de 4 minutos roda em um instante
        scenario = demo_scenario()
        sensor = ScriptedSensor(scenario)
        if max_seconds is None:  # com relógio falso, sem limite o laço nunca pararia
            max_seconds = len(scenario)
        print("Sensores falsos (roteiro de 4 momentos, 60 s cada).")
    else:
        from pulso.sensors.windows import WindowsSensor

        clock = SystemClock()
        sensor = WindowsSensor(clock)
        print("Sensores reais. Ctrl+C para parar.")

    engine = NumpyEngine(seed=1)
    decoder = MoodDecoder(engine.groups)
    seconds = 0

    def on_frame(frame: SensorFrame) -> None:
        nonlocal seconds
        seconds += 1
        previous = decoder.mood
        mood = decoder.update(engine.step(encode(frame), 100).counts)
        if mood is not None:
            note = "  (mudou)" if previous is not None and mood != previous else ""
            print(f"{seconds:4d} s  humor: {mood}{note}", flush=True)

    try:
        SensorLoop(sensor, clock).run(on_frame, max_ticks=max_seconds)
    except KeyboardInterrupt:
        print("\nParado.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulso", description="Pulso, o companheiro de desktop.")
    parser.add_argument("--version", action="version", version=f"pulso {__version__}")
    parser.add_argument(
        "--print-sensors",
        action="store_true",
        help="imprime uma linha por segundo com o que o Pulso sente (desenvolvimento)",
    )
    parser.add_argument(
        "--print-brain",
        action="store_true",
        help="imprime o humor escolhido pela rede a cada 10 s (desenvolvimento)",
    )
    parser.add_argument(
        "--fake-sensors",
        action="store_true",
        help="com --print-brain: usa o roteiro falso em vez de ler o PC",
    )
    parser.add_argument(
        "--max-seconds", type=int, default=None, help="com --print-brain: para depois de N segundos"
    )
    args = parser.parse_args(argv)
    if args.print_sensors:
        _print_sensors()
        return 0
    if args.print_brain:
        _print_brain(args.fake_sensors, args.max_seconds)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
