"""Kompatibilitäts-Wrapper – bitte `python -m scripts.run_backtesting` verwenden."""
import os

os.environ["ENERGY_OPTIMIZER_OFFLINE"] = "1"

from scripts.run_backtesting import main

if __name__ == "__main__":
    main()
