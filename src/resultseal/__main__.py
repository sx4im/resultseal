"""Top-level package execution entrypoint for ``python -m resultseal``."""

from __future__ import annotations

import sys

from resultseal.cli import main

if __name__ == "__main__":
    sys.exit(main())
