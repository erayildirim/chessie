# Third-party notices

**Chessie** — Copyright © 2024 Eray Yıldırım ([@erayildirim](https://github.com/erayildirim)).

This project is licensed under the GNU GPL v3 (see `LICENSE`), which is
compatible with the GPL-licensed libraries and engine it relies on
(PyQt5, python-chess, Stockfish). The following third-party components are
used under their own terms.

## Stockfish (not included)

[Stockfish](https://stockfishchess.org) is licensed under the
[GNU GPL v3](https://github.com/official-stockfish/Stockfish/blob/master/Copying.txt).
It is **not** distributed in this repository. The app runs it as a separate
program and talks to it over the UCI protocol; users download it themselves.
If you redistribute a Stockfish binary (for example in a release zip), include
its `Copying.txt` license and a link to the corresponding source code.

## Chess piece images – `assets/pieces/`

Based on the Wikimedia Commons chess pieces by
[Colin M.L. Burnett (Cburnett)](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces),
modified by Uray M. János (2013–2018).
Licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
These files keep that license (share-alike); the original attribution comments
are preserved inside each SVG.

## Puzzles – `data/puzzles.json`

The mate-in-N positions come from historical games collected by Tim Harvey at
[wtharvey.com](https://wtharvey.com). Solutions were validated and completed with
Stockfish (`tools/repair_puzzles.py`).

## Python libraries

| Library | License |
|---|---|
| [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) | GPL v3 (or commercial) |
| [python-chess](https://github.com/niklasf/python-chess) | GPL v3 |
| [matplotlib](https://matplotlib.org) | PSF-style (matplotlib license) |
| [requests](https://github.com/psf/requests) | Apache 2.0 |
| [openai](https://github.com/openai/openai-python) | Apache 2.0 |

Libraries are installed by the user via `pip` and are not bundled in this repository.
