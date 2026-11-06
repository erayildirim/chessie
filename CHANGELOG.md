# Changelog

## 1.1.0 — Preparing for publication

- Project reorganised into the `chess_trainer` package with a single entry point (`run.py`)
- All absolute paths removed; assets, database and engine are located relative to the project
- **Security:** hardcoded API key removed; passwords hashed with PBKDF2-SHA256 (old plaintext
  passwords are upgraded automatically on login); Lichess request parameters URL-encoded;
  user database excluded from version control
- **AI explanation** rewritten: provider-agnostic (Ollama / Gemini / Groq / OpenRouter / OpenAI),
  grounded in local Stockfish MultiPV analysis, with an engine-only fallback
- Stockfish no longer bundled; auto-detected from `Stockfish/`, `PATH` or `STOCKFISH_PATH`
- Puzzle data: 33 broken/truncated solutions repaired and verified with Stockfish;
  puzzles now shipped as `data/puzzles.json`
- Fixes: crash on draws, stalemate counted as a loss, pawn promotion impossible,
  undo/redo turn desync, engine move after resigning, crash on the profile page for new users,
  black-to-move puzzles unsolvable, solved puzzles later timing out and losing ELO,
  repeated ELO penalties for one puzzle, crash when clicking the board before loading a puzzle,
  ELO values outside the engine's supported range, duplicate usernames on profile update

## 1.0.0 — Graduation project (2024)

Development log (original, Turkish):

- **10.06** – Satranç tahtası, taş hareketleri ve süreler oluşturuldu
- **11.06** – Stockfish motoru bağlandı ve siyah taşlar motor kontrolüne devredildi
- **12.06** – FEN kopyalama ve oyun başlatma butonları eklendi
- **13.06** – Lichess API ve Stockfish motoru önerileri eklendi
- **14.06** – Taş hareketlerine animasyon eklendi
- **24.06** – Animasyondaki sıkıntılar çözüldü. GPT-4o önerileri eklendi.
- **30.06** – Login ve Register eklendi. Database eklendi. Formlar arası geçiş eklendi. PGN eklendi. Hamle ileri geri alma eklendi.
- **01.07** – Studies eklendi. Puzzle'lar eklendi. Puzzle çözme mekanikleri ve Elo hesapları eklendi. Elo grafiği eklendi.
- **03.07** – Arayüz modern şekilde güncellendi. Genel ELO sistemi eklendi. Süre ayarları eklendi. Ses efektleri eklendi.
- **04.07** – Arayüz güncellemeleri.
- **05.07** – Profil sayfası eklendi. Grafikler ve istatistikler eklendi. Program içinde gezinme eklendi.
