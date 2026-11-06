"""Download a puzzle page from wtharvey.com and save it as plain text.

This was used once to collect the bundled puzzles. Please respect the site's
terms and its author's work; the puzzles are credited in THIRD_PARTY_NOTICES.md.

Usage:
    python tools/scrape_puzzles.py <url> <output.txt>
    e.g. python tools/scrape_puzzles.py https://wtharvey.com/ap4.html puzzles.txt
"""
import sys

import requests
from bs4 import BeautifulSoup


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    url, out_path = sys.argv[1], sys.argv[2]

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    content = BeautifulSoup(response.content, "html.parser").get_text()

    # Split the page into one block per puzzle
    puzzles, puzzle = [], ""
    for line in content.split('\n'):
        if "mates in" in line or line.startswith("[ "):
            if puzzle:
                puzzles.append(puzzle.strip())
                puzzle = ""
        puzzle += line + "\n"
    if puzzle:
        puzzles.append(puzzle.strip())

    with open(out_path, "w", encoding='utf-8') as file:
        for puzzle in puzzles:
            file.write(puzzle + "\n\n")
    print(f"{len(puzzles)} blocks saved to {out_path}")


if __name__ == "__main__":
    main()
