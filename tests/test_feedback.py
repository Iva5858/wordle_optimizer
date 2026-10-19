import random

import pytest

from wordle.data import load_answers, load_guesses
from wordle.feedback import code_to_pattern, feedback, feedback_matrix


@pytest.mark.parametrize(
    "guess, answer, expected",
    [
        ("crane", "crane", "22222"),
        ("salet", "funky", "00000"),
        ("speed", "abide", "00101"),  # only one E is yellow: ABIDE has a single E
        ("geese", "eagle", "11002"),  # the green E uses up one of EAGLE's two E's
        ("lolly", "allow", "11200"),  # ALLOW has two L's: one green, one yellow, the third gray
        ("eerie", "cheer", "11100"),
    ],
)
def test_feedback(guess, answer, expected):
    assert feedback(guess, answer) == expected


def test_matrix_matches_feedback():
    rng = random.Random(0)
    guesses = rng.sample(load_guesses(), 300) + ["speed", "geese", "lolly", "eerie"]
    answers = rng.sample(load_answers(), 300) + ["abide", "eagle", "allow", "cheer"]
    matrix = feedback_matrix(guesses, answers)
    for i, guess in enumerate(guesses):
        for j, answer in enumerate(answers):
            assert code_to_pattern(int(matrix[i, j])) == feedback(guess, answer)
