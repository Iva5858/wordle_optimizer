"""The colors a guess gets against an answer.

Feedback is written as five digits, one per letter: 2 = green (right letter,
right spot), 1 = yellow (in the word, wrong spot), 0 = gray. For bulk work it
is also encoded as a base-3 number, one digit per letter, so all green is
the largest code.
"""

import numpy as np

WORD_LENGTH = 5
PATTERN_COUNT = 3**WORD_LENGTH  # number of possible feedback patterns
ALL_GREEN = "2" * WORD_LENGTH
ALL_GREEN_CODE = int(ALL_GREEN, 3)


def feedback(guess: str, answer: str) -> str:
    """Feedback for one guess, following Wordle's rules for repeated letters.

    A letter is yellow only while the answer still has an unmatched copy of
    it, so guessing EERIE against CHEER marks just as many E's as CHEER has.
    """
    unmatched = {}
    for g, a in zip(guess, answer, strict=True):
        if g != a:
            unmatched[a] = unmatched.get(a, 0) + 1

    pattern = []
    for g, a in zip(guess, answer, strict=True):
        if g == a:
            pattern.append("2")
        elif unmatched.get(g, 0):
            pattern.append("1")
            unmatched[g] -= 1
        else:
            pattern.append("0")
    return "".join(pattern)


def code_to_pattern(code: int) -> str:
    """The five-digit pattern for a base-3 feedback code."""
    return np.base_repr(code, 3).zfill(WORD_LENGTH)


def feedback_matrix(guesses: list[str], answers: list[str], chunk: int = 1024) -> np.ndarray:
    """Feedback codes for every guess against every answer, shape (guesses, answers)."""
    G = np.array([[ord(c) for c in w] for w in guesses], dtype=np.uint8)
    A = np.array([[ord(c) for c in w] for w in answers], dtype=np.uint8)
    codes = np.empty((len(guesses), len(answers)), dtype=np.uint8)
    for start in range(0, len(guesses), chunk):  # in blocks, to keep memory use small
        codes[start : start + chunk] = _feedback_block(G[start : start + chunk], A)
    return codes


def _feedback_block(G: np.ndarray, A: np.ndarray) -> np.ndarray:
    green = [G[:, i, None] == A[None, :, i] for i in range(WORD_LENGTH)]
    codes = np.zeros((len(G), len(A)), dtype=np.uint8)
    for i in range(WORD_LENGTH):
        letter = G[:, i, None]
        # Copies of this letter in the answer that aren't matched by a green...
        unmatched = sum((A[None, :, k] == letter) & ~green[k] for k in range(WORD_LENGTH))
        # ...minus the ones already claimed by earlier yellows in the guess
        claimed = sum((G[:, j, None] == letter) & ~green[j] for j in range(i))
        yellow = ~green[i] & (unmatched > claimed)
        codes = codes * 3 + np.where(green[i], 2, np.where(yellow, 1, 0)).astype(np.uint8)
    return codes
