"""Import "mate in N" puzzles from a text file (as produced by scrape_puzzles.py)
into the app database.

Usage:
    python tools/import_puzzles.py <puzzles.txt> <N>

After importing, run ``python tools/repair_puzzles.py`` to validate the
solutions with Stockfish and refresh ``data/puzzles.json``.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_trainer import database  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    file_path, mate_in = sys.argv[1], int(sys.argv[2])

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract the puzzles and their solutions
    pattern = re.compile(
        r'(White|Black) mates in %d\..+?\((\d+)\)\s*([^\[]+)\s*\[ ([^\]]+) \]' % mate_in, re.DOTALL)
    games = []
    for match in pattern.findall(content):
        rating = int(match[1])
        fen = match[2].strip()
        solution = re.sub(r'^\.\.\.\s*', '', match[3].strip())  # Remove leading "..."
        games.append((f'matein{mate_in}', rating, fen, solution))

    conn = database.connect()
    conn.executemany('INSERT INTO studies (type, rating, fen, solution) VALUES (?, ?, ?, ?)', games)
    conn.commit()
    conn.close()
    print(f"{len(games)} puzzles inserted into the database.")


if __name__ == "__main__":
    main()
