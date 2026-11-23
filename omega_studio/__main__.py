"""Point d'entrée CLI : `python -m omega_studio [fichier.alg]` ou `omega-studio`."""

from __future__ import annotations

import sys

from .app import run_app


def main() -> None:
    sys.exit(run_app())


if __name__ == "__main__":
    main()
