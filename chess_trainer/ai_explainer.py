"""AI position explanations.

The explanation is grounded in a local Stockfish analysis, which is sent to a
language model together with the position. Any OpenAI-compatible chat API can
be used (configured via AI_BASE_URL / AI_API_KEY / AI_MODEL):

* Ollama (default, free, runs locally, no API key)
* Groq, Google Gemini, OpenRouter, OpenAI ... with the user's *own* key

If no model is reachable, a plain engine-based explanation is returned, so the
feature always produces something useful.
"""
import chess
import chess.engine

from . import config

SYSTEM_PROMPT = (
    "You are an experienced chess coach explaining a position to a club-level player. "
    "Base your explanation strictly on the Stockfish analysis you are given: do not "
    "invent moves or evaluations. Explain who is better and why (material, king safety, "
    "piece activity, pawn structure, threats), what the best move achieves, and the main "
    "plan for the side to move. Be concise (at most ~180 words). Answer in {language}."
)


def _describe_score(score, turn):
    """Human readable (Turkish) evaluation from White's point of view."""
    white = score.white()
    if white.is_mate():
        n = white.mate()
        side = "Beyaz" if n > 0 else "Siyah"
        return f"#{n}", f"{side} {abs(n)} hamlede mat ediyor"
    cp = white.score()
    pawns = cp / 100.0
    if abs(cp) < 50:
        verdict = "Pozisyon dengeli"
    else:
        side = "Beyaz" if cp > 0 else "Siyah"
        if abs(cp) < 150:
            verdict = f"{side} hafif üstün"
        elif abs(cp) < 300:
            verdict = f"{side} açıkça üstün"
        else:
            verdict = f"{side} kazanan durumda"
    return f"{pawns:+.2f}", verdict


def analyse_position(engine, board, multipv=3, seconds=0.5):
    """Return a list of the engine's top lines as dicts (eval, verdict, san line)."""
    infos = engine.analyse(board, chess.engine.Limit(time=seconds), multipv=multipv)
    if isinstance(infos, dict):
        infos = [infos]
    lines = []
    for info in infos:
        pv = info.get("pv") or []
        if not pv or "score" not in info:
            continue
        eval_text, verdict = _describe_score(info["score"], board.turn)
        lines.append({
            "eval": eval_text,
            "verdict": verdict,
            "first": board.san(pv[0]),
            "line": board.variation_san(pv[:8]),
        })
    return lines


def _material(board):
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    w = sum(len(board.pieces(p, chess.WHITE)) * v for p, v in values.items())
    b = sum(len(board.pieces(p, chess.BLACK)) * v for p, v in values.items())
    return w, b


def build_prompt(board, lines):
    side = "White" if board.turn == chess.WHITE else "Black"
    w, b = _material(board)
    engine_text = "\n".join(
        f"{i}. eval {l['eval']} (White's view): {l['line']}" for i, l in enumerate(lines, 1)
    ) or "No engine lines available (game over)."
    return (
        f"FEN: {board.fen()}\n"
        f"Side to move: {side}\n"
        f"Material (White/Black): {w}/{b}\n"
        f"Board (White at the bottom):\n{board}\n\n"
        f"Stockfish top lines:\n{engine_text}\n\n"
        "Explain this position."
    )


def engine_only_explanation(board, lines):
    if board.is_game_over():
        return "Oyun bitti: " + board.result()
    if not lines:
        return "Motor analizi alınamadı."
    best = lines[0]
    text = [
        f"Değerlendirme: {best['eval']} — {best['verdict']}.",
        f"En iyi hamle: {best['first']}",
        f"Ana varyant: {best['line']}",
    ]
    if len(lines) > 1:
        text.append("\nAlternatifler:")
        for l in lines[1:]:
            text.append(f"  • {l['first']} ({l['eval']}): {l['line']}")
    return "\n".join(text)


def ask_model(board, lines):
    """Query the configured language model. Raises on any failure."""
    from openai import OpenAI  # imported lazily so the app starts without network access

    client = OpenAI(
        base_url=config.AI_BASE_URL,
        api_key=config.AI_API_KEY or "not-needed",  # local servers ignore the key
        timeout=config.AI_TIMEOUT,
        max_retries=0,
    )
    completion = client.chat.completions.create(
        model=config.AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(language=config.AI_LANGUAGE)},
            {"role": "user", "content": build_prompt(board, lines)},
        ],
        temperature=0.4,
        max_tokens=600,
    )
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("Model boş yanıt döndürdü.")
    return content.strip()


def explain(board, lines):
    """Return an explanation; falls back to engine-only text if the AI is unavailable."""
    if board.is_game_over():
        return engine_only_explanation(board, lines)
    try:
        return ask_model(board, lines)
    except Exception as e:  # network errors, missing model, bad key, ...
        return (
            engine_only_explanation(board, lines)
            + "\n\n— AI modeline ulaşılamadı, yalnızca motor analizi gösteriliyor. "
            f"({type(e).__name__}: {str(e)[:150]})\n"
            "AI açıklamalarını açmak için README dosyasındaki \"AI Açıklaması\" bölümüne bakın."
        )
