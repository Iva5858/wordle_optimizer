"""The colors a guess gets against an answer.

Feedback is written as five digits, one per letter: 2 = green (right letter,
right spot), 1 = yellow (in the word, wrong spot), 0 = gray. For bulk work it
is also encoded as a base-3 number from 0 to 242, where 242 is all green.
"""
import numpy as np

ALL_GREEN = "22222"
ALL_GREEN_CODE = 242


def feedback(guess: str, answer: str) -> str:
    """Feedback for one guess, following Wordle's rules for repeated letters.

    A letter is yellow only while the answer still has an unmatched copy of
    it, so guessing EERIE against CHEER marks just as many E's as CHEER has.
    """
    unmatched = {}
    for g, a in zip(guess, answer):
        if g != a:
            unmatched[a] = unmatched.get(a, 0) + 1

    pattern = []
    for g, a in zip(guess, answer):
        if g == a:
            pattern.append("2")
        elif unmatched.get(g, 0):
            pattern.append("1")
            unmatched[g] -= 1
        else:
            pattern.append("0")
    return "".join(pattern)


def code_to_pattern(code: int) -> str:
    return np.base_repr(code, 3).zfill(5)


def feedback_matrix(guesses: list[str], answers: list[str]) -> np.ndarray:
    """Feedback codes for every guess against every answer, shape (guesses, answers)."""
    G = np.array([[ord(c) for c in w] for w in guesses], dtype=np.uint8)
    A = np.array([[ord(c) for c in w] for w in answers], dtype=np.uint8)
    green = [G[:, i, None] == A[None, :, i] for i in range(5)]

    codes = np.zeros((len(guesses), len(answers)), dtype=np.uint8)
    for i in range(5):
        letter = G[:, i, None]
        # Copies of this letter in the answer that aren't matched by a green...
        unmatched = sum((A[None, :, k] == letter) & ~green[k] for k in range(5))
        # ...minus the ones already claimed by earlier yellows in the guess
        claimed = sum((G[:, j, None] == letter) & ~green[j] for j in range(i))
        yellow = ~green[i] & (unmatched > claimed)
        codes = codes * 3 + np.where(green[i], 2, np.where(yellow, 1, 0)).astype(np.uint8)
    return codes
