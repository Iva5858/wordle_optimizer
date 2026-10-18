import pytest

from wordle.data import CURRENT_GUESSES_FILE, TREE_FILE, load_answers, load_guesses
from wordle.feedback import feedback
from wordle.player import Player
from wordle.tree import load_tree


@pytest.fixture(scope="module")
def files():
    return load_tree(TREE_FILE), load_answers(), load_guesses(CURRENT_GUESSES_FILE)


def play(files, answer):
    player = Player(*files)
    for _ in range(6):
        guess = player.next_guess()
        player.record(guess, feedback(guess, answer))
        if player.solved:
            return len(player.history)
    return None


def test_solves_every_original_answer(files):
    results = [play(files, a) for a in files[1]]
    assert None not in results
    assert sum(results) / len(results) < 3.43


@pytest.mark.parametrize("answer", ["snafu", "guano", "kazoo", "uvula"])
def test_solves_answers_outside_the_tree(files, answer):
    assert answer not in files[1]
    assert play(files, answer) is not None


def test_rejects_impossible_feedback(files):
    player = Player(*files)
    player.record("salet", "00000")
    with pytest.raises(ValueError):
        player.record("crane", "00002")  # E can't be green after SALET said there's no E
    assert len(player.history) == 1  # the bad feedback didn't change the game
