#!/usr/bin/env python
"""Point d'entrée Django pour les commandes administratives."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez que l'environnement virtuel est activé."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
