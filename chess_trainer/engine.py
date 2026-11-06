"""Locating and configuring the Stockfish engine.

Stockfish is GPL-3.0 licensed and is *not* shipped in this repository.
It is looked up in this order:
  1. the STOCKFISH_PATH environment variable / .env entry
  2. any ``stockfish*`` executable inside the project's ``Stockfish/`` folder
  3. ``stockfish`` on the system PATH
"""
import glob
import os
import shutil

import chess.engine

from . import config


class EngineNotFoundError(RuntimeError):
    pass


def find_stockfish():
    if config.STOCKFISH_PATH and os.path.isfile(config.STOCKFISH_PATH):
        return config.STOCKFISH_PATH

    for base in {config.APP_DIR, config.ROOT_DIR}:
        pattern = os.path.join(base, "Stockfish", "**", "stockfish*")
        for candidate in sorted(glob.glob(pattern, recursive=True)):
            if os.path.isfile(candidate) and (os.name != "nt" or candidate.lower().endswith(".exe")):
                return candidate

    on_path = shutil.which("stockfish")
    if on_path:
        return on_path

    raise EngineNotFoundError(
        "Stockfish bulunamadı. https://stockfishchess.org/download/ adresinden indirip "
        "'Stockfish/' klasörüne koyun veya .env dosyasında STOCKFISH_PATH ayarlayın.\n\n"
        "Stockfish not found. Download it from https://stockfishchess.org/download/ and "
        "put it in the 'Stockfish/' folder, or set STOCKFISH_PATH in your .env file."
    )


def open_engine():
    return chess.engine.SimpleEngine.popen_uci(find_stockfish())


def set_engine_elo(engine, elo):
    """Limit engine strength, clamping to the range the engine supports."""
    option = engine.options.get("UCI_Elo")
    if option is None:
        return
    try:
        elo = int(elo)
    except (TypeError, ValueError):
        elo = option.default
    elo = max(option.min, min(option.max, elo))
    engine.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})
