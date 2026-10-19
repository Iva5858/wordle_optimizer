"""Choosing guesses during a live game."""

from functools import lru_cache

import numpy as np

from .data import CURRENT_GUESSES_FILE, LIVE_TREE_FILE, load_guesses
from .feedback import ALL_GREEN
from .search import TreeSolver, cached_solver
from .tree import follow, guess_at, load_tree

MAX_GUESSES = 6
SAFETY_CHECK_FROM = 5  # check guesses for safety once this many guesses (or fewer) are left


@lru_cache(maxsize=2)
def _solver_for(guesses: tuple) -> TreeSolver:
    """One solver over every allowed word, shared by all games so its caches are reused."""
    return cached_solver(list(guesses), list(guesses), width=1.0)


class Player:
    """Picks the guesses for one game.

    It keeps two sets of words that fit the feedback so far:
      * candidates: the answers the tree was built for (likely answers), or,
        once none of those fit, every allowed word that does
      * possible: every allowed word, since NYT can always pick a new one

    It follows the tree while the game stays on it, and otherwise searches the
    candidates live. From the second guess on, it also checks that its guess
    still leaves a way to find every *possible* word in time, and switches to a
    guess that does if not, so a word the tree has never seen can't make it lose.
    """

    def __init__(self, tree, answers, guesses):
        self.solver = _solver_for(tuple(guesses))
        self.node = tree
        self._candidates = self._indices(answers)
        self._possible = self.solver.all_answers()
        self.history = []

    @classmethod
    def from_files(cls, tree_file=LIVE_TREE_FILE) -> "Player":
        """A player for the bundled live tree and today's allowed guesses."""
        tree, answers = load_tree(tree_file)
        return cls(tree, answers, load_guesses(CURRENT_GUESSES_FILE))

    @property
    def candidates(self) -> list[str]:
        """The likely answers that still fit the feedback."""
        return [self.solver.answers[i] for i in self._candidates]

    @property
    def possible(self) -> list[str]:
        """Every allowed word that still fits the feedback."""
        return [self.solver.answers[i] for i in self._possible]

    @property
    def on_tree(self) -> bool:
        """Whether the game is still following the tree."""
        return self.node is not None

    @property
    def solved(self) -> bool:
        """Whether the last guess was all green."""
        return bool(self.history) and self.history[-1][1] == ALL_GREEN

    def next_guess(self) -> str:
        """The guess to play next."""
        solver = self.solver
        preferred = self._preferred_guess()
        guesses_left = MAX_GUESSES - len(self.history)
        if guesses_left > SAFETY_CHECK_FROM:
            return preferred

        # Take the first guess that still lets every possible word be found in time:
        # ours, then the best ones for the likely answers, then the best for everything
        options = [
            solver.index[preferred],
            *solver.ranked(self._candidates, limit=100),
            *solver.ranked(self._possible, limit=200),
        ]
        safe = next((g for g in options if solver.is_safe(g, self._possible, guesses_left)), None)
        return preferred if safe is None else solver.guesses[safe]

    def _preferred_guess(self) -> str:
        if self.on_tree:
            return guess_at(self.node)
        if len(self._candidates) <= 2:
            return self.solver.answers[self._candidates[0]]
        return self.solver.best_guess(self._candidates)

    def record(self, guess: str, pattern: str) -> None:
        """Update the game with the feedback a guess received.

        Raises ValueError, leaving the game unchanged, if no allowed word fits.
        """
        code = int(pattern, 3)
        row = self.solver.matrix[self.solver.index[guess]]
        possible = self._possible[row[self._possible] == code]
        if not len(possible):
            raise ValueError(f"no allowed word fits {guess.upper()} = {pattern}")
        likely = self._candidates[row[self._candidates] == code]
        on_tree = len(likely) and self.on_tree and guess == guess_at(self.node)
        self.node = follow(self.node, pattern) if on_tree else None
        self._candidates = likely if len(likely) else possible
        self._possible = possible
        self.history.append((guess, pattern))

    def _indices(self, words) -> np.ndarray:
        return np.array(sorted(self.solver.index[w] for w in words), dtype=np.int64)
