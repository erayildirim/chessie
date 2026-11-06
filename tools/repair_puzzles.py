"""Validate (and repair) every puzzle solution with Stockfish, then export
the puzzle set to ``data/puzzles.json``.

The original solutions were scraped from text and many were truncated or
contained notes such as "if Kxe6 or Kd6".  This script keeps the original
key move whenever it still forces mate and lets the engine fill in a complete,
verified mating line.

Usage:
    python tools/repair_puzzles.py [path/to/source.db]
"""
import json
import os
import sqlite3
import sys

import chess
import chess.engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chess_trainer.engine import find_stockfish  # noqa: E402


def stored_moves(board, solution):
    """Return the legal prefix of a stored SAN solution."""
    b = board.copy()
    moves = []
    for token in solution.split():
        try:
            moves.append(b.push_san(token))
        except ValueError:
            break
    return moves


def is_complete(board, moves):
    b = board.copy()
    for m in moves:
        b.push(m)
    return bool(moves) and b.is_checkmate()


def engine_line(engine, board, first_move=None):
    b = board.copy()
    if first_move is not None:
        b.push(first_move)
        if b.is_checkmate():
            return [first_move]
    info = engine.analyse(b, chess.engine.Limit(time=3, depth=30))
    score = info["score"].pov(board.turn)
    if not score.is_mate() or score.mate() <= 0:
        return None
    line = ([first_move] if first_move else []) + info.get("pv", [])
    if not is_complete(board, line):
        return None
    return line


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "chess.db")
    conn = sqlite3.connect(src)
    rows = conn.execute("SELECT id, type, rating, fen, solution FROM studies ORDER BY id").fetchall()
    conn.close()

    engine = chess.engine.SimpleEngine.popen_uci(find_stockfish())
    puzzles, repaired = [], 0
    try:
        for pid, ptype, rating, fen, solution in rows:
            board = chess.Board(fen)
            moves = stored_moves(board, solution)
            if not is_complete(board, moves):
                line = engine_line(engine, board, moves[0] if moves else None) or engine_line(engine, board)
                if line is None:
                    print(f"[skip] #{pid}: no forced mate found")
                    continue
                moves = line
                repaired += 1
            san, b = [], board.copy()
            for m in moves:
                san.append(b.san(m))
                b.push(m)
            mate_in = (len(moves) + 1) // 2
            new_type = f"matein{mate_in}"
            if new_type != ptype or " ".join(san) != solution:
                print(f"#{pid}: {ptype} '{solution}' -> {new_type} '{' '.join(san)}'")
            puzzles.append({"id": pid, "type": new_type, "rating": rating,
                            "fen": fen, "solution": " ".join(san)})
    finally:
        engine.quit()

    out = os.path.join(ROOT, "data", "puzzles.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(puzzles, f, indent=1, ensure_ascii=False)
    print(f"\n{len(puzzles)} puzzles exported to {out} ({repaired} repaired)")


if __name__ == "__main__":
    main()
