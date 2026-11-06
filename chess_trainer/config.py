"""Central configuration: file paths and user settings.

Settings are read from environment variables. For convenience, a ``.env``
file in the project root is loaded automatically (see ``.env.example``).
"""
import os
import sys


def _project_root():
    # When bundled with PyInstaller, bundled files live in sys._MEIPASS.
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT_DIR = _project_root()
# Writable location (next to the executable when frozen, project root otherwise).
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else ROOT_DIR


def _load_dotenv(path):
    """Minimal .env loader (KEY=VALUE lines); never overrides real env vars."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv(os.path.join(APP_DIR, ".env"))

ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
PUZZLES_JSON = os.path.join(ROOT_DIR, "data", "puzzles.json")

DB_PATH = os.environ.get("CHESS_DB_PATH") or os.path.join(APP_DIR, "data", "chess.db")
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "")

# AI explanation settings. Any OpenAI-compatible endpoint works.
# The default targets a local Ollama server, which is free and needs no API key.
AI_BASE_URL = os.environ.get("AI_BASE_URL", "http://localhost:11434/v1")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "llama3.2")
AI_LANGUAGE = os.environ.get("AI_LANGUAGE", "Turkish")
AI_TIMEOUT = float(os.environ.get("AI_TIMEOUT", "60"))


def image(name):
    return os.path.join(IMAGES_DIR, name)


def piece(name):
    return os.path.join(PIECES_DIR, name)


def sound(name):
    return os.path.join(SOUNDS_DIR, name)


PIECE_TO_SVG = {
    'P': piece('pawn-w.svg'), 'N': piece('knight-w.svg'), 'B': piece('bishop-w.svg'),
    'R': piece('rook-w.svg'), 'Q': piece('queen-w.svg'), 'K': piece('king-w.svg'),
    'p': piece('pawn-b.svg'), 'n': piece('knight-b.svg'), 'b': piece('bishop-b.svg'),
    'r': piece('rook-b.svg'), 'q': piece('queen-b.svg'), 'k': piece('king-b.svg'),
}
