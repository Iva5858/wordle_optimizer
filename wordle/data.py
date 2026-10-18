"""The bundled word lists, and where files live on disk."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS_DIR = ROOT / "words"
CACHE_DIR = ROOT / ".cache"
RESULTS_DIR = ROOT / "wordle_results"

ANSWERS_FILE = WORDS_DIR / "answers.txt"                    # the original 2,315 answers
ORIGINAL_GUESSES_FILE = WORDS_DIR / "original_guesses.txt"  # the original 10,657 other allowed guesses
CURRENT_GUESSES_FILE = WORDS_DIR / "current_guesses.txt"    # every guess NYT accepts today
PAST_ANSWERS_FILE = WORDS_DIR / "past_answers.txt"          # real NYT answers, in order

# Strategies written by solve.py
LEADERBOARD_TREE_FILE = WORDS_DIR / "leaderboard_tree.json"  # original lists only, for comparing solvers
LIVE_TREE_FILE = WORDS_DIR / "live_tree.json"                # what the bot plays: covers every NYT answer so far


def load_words(path) -> list[str]:
    """Read a word list: one five-letter word per line, returned sorted and lowercase."""
    with open(path) as f:
        return sorted({line.strip().lower() for line in f if len(line.strip()) == 5})


def load_answers() -> list[str]:
    return load_words(ANSWERS_FILE)


def load_known_answers() -> list[str]:
    """The original answers plus every answer NYT has actually used."""
    return sorted(set(load_answers()) | set(load_words(PAST_ANSWERS_FILE)))


def load_guesses(path=ORIGINAL_GUESSES_FILE) -> list[str]:
    """Allowed guesses from a list, plus the answers (which are always allowed)."""
    return sorted(set(load_words(path)) | set(load_answers()))
