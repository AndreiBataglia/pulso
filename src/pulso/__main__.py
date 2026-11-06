"""Ponto de entrada do comando `pulso`."""

import argparse

from pulso import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulso", description="Pulso, o companheiro de desktop.")
    parser.add_argument("--version", action="version", version=f"pulso {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
