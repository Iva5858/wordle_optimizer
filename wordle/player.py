"""Choosing guesses during a live game."""
from .data import CURRENT_GUESSES_FILE, LIVE_TREE_FILE, load_guesses
from .feedback import ALL_GREEN, feedback
from .search import TreeSolver
from .tree import follow, guess_at, load_tree

MAX_GUESSES = 6


class Player:
    """Picks the guesses for one game.

    It keeps two lists of words that fit the feedback so far:
      * candidates: the answers the tree was built for (likely answers), or,
        once none of those fit, every allowed word that does
      * possible: every allowed word, since NYT can always pick a new one

    It follows the tree while the game stays on it, and otherwise searches the
    candidates live. Near the end it also checks that its guess still leaves a
    way to find every *possible* word in time, and switches to a guess that
    does if not, so a word the tree has never seen can't make it lose.
    """

    def __init__(self, tree, answers, guesses, width=1.0):
        self.node = tree
        self.candidates = list(answers)
        self.possible = list(guesses)
        self.guesses = guesses
        self.width = width
        self.history = []

    @classmethod
    def from_files(cls, tree_file=LIVE_TREE_FILE, **kwargs):
        tree, answers = load_tree(tree_file)
        return cls(tree, answers, load_guesses(CURRENT_GUESSES_FILE), **kwargs)

    @property
    def on_tree(self) -> bool:
        return self.node is not None

    @property
    def solved(self) -> bool:
        return bool(self.history) and self.history[-1][1] == ALL_GREEN

    def next_guess(self) -> str:
        guess = self._preferred_guess()
        guesses_left = MAX_GUESSES - len(self.history)
        if guesses_left > 4:
            return guess  # with four or more guesses to spare after this one, any guess is safe
        possible = TreeSolver(self.guesses, self.possible, width=self.width)
        if possible.is_safe(self.guesses.index(guess), possible.all_answers(), guesses_left):
            return guess
        return possible.safe_guess(guesses_left) or guess

    def _preferred_guess(self) -> str:
        if self.on_tree:
            return guess_at(self.node)
        if len(self.candidates) <= 2:
            return self.candidates[0]
        return TreeSolver(self.guesses, self.candidates, width=self.width).best_guess()

    def record(self, guess: str, pattern: str):
        """Update the game with the feedback a guess received.

        Raises ValueError, leaving the game unchanged, if no allowed word fits.
        """
        possible = [w for w in self.possible if feedback(guess, w) == pattern]
        if not possible:
            raise ValueError(f"no allowed word fits {guess.upper()} = {pattern}")
        likely = [w for w in self.candidates if feedback(guess, w) == pattern]
        on_tree = likely and self.on_tree and guess == guess_at(self.node)
        self.node = follow(self.node, pattern) if on_tree else None
        self.candidates = likely or possible
        self.possible = possible
        self.history.append((guess, pattern))
