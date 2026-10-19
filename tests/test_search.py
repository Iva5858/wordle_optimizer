import random
from collections import Counter
from functools import cache

import pytest

from wordle.data import load_answers, load_guesses
from wordle.feedback import ALL_GREEN, feedback
from wordle.search import EXACT, TreeSolver
from wordle.tree import play

# Answers that are hard to tell apart, plus a few unrelated ones
HARD = [
    "fight",
    "light",
    "might",
    "night",
    "right",
    "sight",
    "tight",
    "wight",
    "eight",
    "batch",
    "catch",
    "hatch",
    "latch",
    "match",
    "patch",
    "watch",
    "crane",
    "pious",
]


def brute_force(guesses, answers):
    """The exact minimum total guesses, trying every guess at every node."""

    @cache
    def cost(subset):
        if len(subset) == 1:
            return 1
        best = float("inf")
        for g in guesses:
            groups = {}
            for a in subset:
                groups.setdefault(feedback(g, a), []).append(a)
            if len(groups) == 1:
                continue
            total = len(subset) + sum(cost(tuple(s)) for p, s in groups.items() if p != ALL_GREEN)
            best = min(best, total)
        return best

    return cost(tuple(answers))


@pytest.mark.parametrize("seed", range(4))
def test_finds_the_optimum(seed):
    rng = random.Random(seed)
    answers = sorted(set(rng.sample(HARD, 10) + rng.sample(load_answers(), 4)))
    guesses = sorted(
        set(answers) | set(rng.sample(load_guesses(), 40)) | {"flamb", "chawk", "wight"}
    )
    assert TreeSolver(guesses, answers, width=EXACT).solve()[0] == brute_force(guesses, answers)


def test_tree_matches_its_cost():
    answers = sorted(HARD)
    solver = TreeSolver(load_guesses(), answers, width=1)
    tree = solver.tree()
    assert sum(len(play(tree, a)) for a in answers) == solver.solve()[0]
    assert all(play(tree, a)[-1] == a for a in answers)


@pytest.mark.parametrize("size", [5, 24, 25, 60])  # both sides of the small-set shortcut
def test_scores_count_groups(size):
    rng = random.Random(size)
    guesses = load_guesses()
    answers = rng.sample(load_answers(), size)
    solver = TreeSolver(guesses, answers)
    score, largest = solver.scores(solver.all_answers())
    for g in rng.sample(range(len(guesses)), 50):
        sizes = Counter(feedback(guesses[g], a) for a in answers).values()
        assert largest[g] == max(sizes)
        if max(sizes) < size:  # guesses that split nothing are scored as infinite
            bonus = 1.5 if guesses[g] in answers else 0
            assert score[g] == sum(s * s for s in sizes) - bonus


def test_answers_must_be_guesses():
    with pytest.raises(ValueError):
        TreeSolver(["crane"], ["crane", "pious"])
