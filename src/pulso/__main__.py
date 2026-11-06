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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulso", description="Pulso, o companheiro de desktop.")
    parser.add_argument("--version", action="version", version=f"pulso {__version__}")
    parser.add_argument(
        "--print-sensors",
        action="store_true",
        help="imprime uma linha por segundo com o que o Pulso sente (desenvolvimento)",
    )
    args = parser.parse_args(argv)
    if args.print_sensors:
        _print_sensors()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
