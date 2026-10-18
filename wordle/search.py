"""Search for the Wordle strategy that needs the fewest guesses in total.

A strategy is a decision tree: a guess, then for each feedback pattern the
next node. For a set S of possible answers, choosing guess g costs

    cost(S, g) = |S| + sum(cost(B) for each group B of S that g doesn't solve)

because every answer in S spends this guess, and the unsolved ones continue
into the subtree for the feedback they produced. The solver minimizes this
recursively, made fast by:

* Shortcuts: a guess that splits S into single answers is provably optimal
  (2|S| - 1 guesses if it is one of the answers, 2|S| otherwise).
* A beam: only the most promising guesses (smallest expected group size) are
  tried at each node, more of them for larger sets. `width` scales how many.
* Branch and bound: a guess is abandoned as soon as a lower bound on its cost
  reaches the best cost found so far.
* Memoized subsets, and the subtrees under each opening guess are solved in
  parallel on every CPU core.
"""
import hashlib
from dataclasses import dataclass
from multiprocessing import Pool

import numpy as np

from .data import CACHE_DIR
from .feedback import ALL_GREEN, ALL_GREEN_CODE, code_to_pattern, feedback_matrix


def lower_bound(n: int) -> int:
    """Fewest total guesses any strategy can spend on n answers."""
    return 2 * n - 1 if n else 0


class TreeSolver:
    """Finds a low-cost decision tree for a list of possible answers.

    Answer subsets are numpy arrays of indices into `answers`, and guesses are
    indices into `guesses`. Every answer must also be an allowed guess.
    """

    def __init__(self, guesses, answers, matrix=None, width=10.0):
        self.guesses = list(guesses)
        self.answers = list(answers)
        self.matrix = feedback_matrix(self.guesses, self.answers) if matrix is None else matrix
        self.width = width
        index = {word: i for i, word in enumerate(self.guesses)}
        missing = [a for a in self.answers if a not in index]
        if missing:
            raise ValueError(f"answers must also be allowed guesses, missing: {missing[:5]}")
        self.answer_guess = np.array([index[a] for a in self.answers], dtype=np.int64)
        self._row_offsets = (np.arange(len(self.guesses)) * 243)[:, None]
        self._memo = {}

    def all_answers(self) -> np.ndarray:
        return np.arange(len(self.answers))

    def beam(self, n: int) -> int:
        """How many guesses to try at a node with n possible answers."""
        base = 40 if n > 100 else 20 if n > 30 else 10 if n > 10 else 5
        return max(1, int(base * self.width))

    def scores(self, S):
        """Score every guess for answer subset S (lower is more promising).

        Returns the scores and each guess's largest group size. The score is
        the sum of squared group sizes, i.e. proportional to the expected
        number of answers left after the guess.
        """
        codes = self.matrix[:, S].astype(np.int32) + self._row_offsets
        counts = np.bincount(codes.ravel(), minlength=len(self.guesses) * 243).reshape(-1, 243)
        largest = counts.max(axis=1)
        score = (counts.astype(np.int64) ** 2).sum(axis=1).astype(np.float64)
        score[self.answer_guess[S]] -= 1.5   # a guess that could win right away is worth a bit more
        score[largest == len(S)] = np.inf    # the guess doesn't tell these answers apart at all
        return score, largest

    def groups(self, g, S):
        """Answers in S grouped by the feedback guess g gets, largest group first.

        Returns (feedback code, subset) pairs, leaving out the answer g solves.
        """
        codes = self.matrix[g, S]
        order = np.argsort(codes, kind="stable")
        codes, S = codes[order], S[order]
        cuts = np.flatnonzero(np.diff(codes)) + 1
        groups = [(int(c[0]), s) for c, s in zip(np.split(codes, cuts), np.split(S, cuts))
                  if c[0] != ALL_GREEN_CODE]
        return sorted(groups, key=lambda group: -len(group[1]))

    def solve(self, S=None):
        """Return (total guesses, guess index) for the best strategy found for S."""
        if S is None:
            S = self.all_answers()
        n = len(S)
        if n <= 2:
            return 2 * n - 1, self.answer_guess[S[0]]
        key = S.tobytes()
        if key not in self._memo:
            self._memo[key] = self._solve(S)
        return self._memo[key]

    def _solve(self, S):
        n = len(S)
        score, largest = self.scores(S)

        in_set = self.answer_guess[S]
        splits_answers = in_set[largest[in_set] == 1]
        if len(splits_answers):
            return 2 * n - 1, splits_answers[0]
        splits = np.flatnonzero(largest == 1)
        if len(splits):
            return 2 * n, splits[0]

        k = min(self.beam(n), len(score))
        candidates = np.argpartition(score, k - 1)[:k]
        candidates = candidates[np.argsort(score[candidates], kind="stable")]

        best_cost, best_guess = np.inf, None
        for g in candidates:
            if not np.isfinite(score[g]):
                break
            groups = self.groups(g, S)
            cost = n + sum(lower_bound(len(s)) for _, s in groups)
            if cost >= best_cost:
                continue
            # Replace each group's lower bound with its real cost, stopping early if hopeless
            for _, s in groups:
                cost += self.solve(s)[0] - lower_bound(len(s))
                if cost >= best_cost:
                    break
            else:
                best_cost, best_guess = cost, g
        return best_cost, best_guess

    def best_guess(self, S=None) -> str:
        return self.guesses[self.solve(S)[1]]

    def can_finish(self, S, guesses_left: int) -> bool:
        """Whether every answer in S can be found within `guesses_left` guesses.

        Checked exactly up to three guesses (trying the most promising guesses
        first). Four or more are assumed to be enough, which benchmark.py
        verifies by playing every allowed word.
        """
        if guesses_left >= 4:
            return True
        if len(S) == 1:
            return guesses_left >= 1
        if guesses_left <= 1:
            return False
        score, largest = self.scores(S)
        if guesses_left == 2:
            return bool((largest == 1).any())  # one guess must split S into single words
        return any(self.is_safe(g, S, guesses_left) for g in self._ranked(score))

    def is_safe(self, g, S, guesses_left: int) -> bool:
        """Whether guessing g now still lets every answer in S be found in time."""
        return all(self.can_finish(s, guesses_left - 1) for _, s in self.groups(g, S))

    def safe_guess(self, guesses_left: int):
        """The most promising guess that is safe for all answers, or None."""
        S = self.all_answers()
        score, _ = self.scores(S)
        return next((self.guesses[g] for g in self._ranked(score, limit=500)
                     if self.is_safe(g, S, guesses_left)), None)

    def _ranked(self, score, limit=50):
        """Up to `limit` guesses that split the set, most promising first."""
        order = np.argsort(score, kind="stable")[:limit]
        return [g for g in order if np.isfinite(score[g])]

    def tree(self, S=None):
        """The strategy for S as nested dicts: {"guess": word, "map": {feedback: subtree}}.

        A subtree that is down to a single answer is just that word.
        """
        if S is None:
            S = self.all_answers()
        if len(S) == 1:
            return self.answers[S[0]]
        return self._node(self.solve(S)[1], S)

    def _node(self, g, S):
        node = {"guess": self.guesses[g], "map": {}}
        if g in self.answer_guess[S]:
            node["map"][ALL_GREEN] = self.guesses[g]
        for code, s in self.groups(g, S):
            node["map"][code_to_pattern(code)] = self.tree(s)
        return node


@dataclass
class Strategy:
    opener: str
    total_guesses: int
    tree: dict


def solve_openers(guesses, answers, openers, width=10.0, processes=None) -> list[Strategy]:
    """Find the best tree for each opening guess, using every CPU core. Best first."""
    matrix_file = _cached_matrix(guesses, answers)
    solver = TreeSolver(guesses, answers, np.load(matrix_file, mmap_mode="r"), width)
    index = {word: i for i, word in enumerate(solver.guesses)}
    unknown = [w for w in openers if w not in index]
    if unknown:
        raise ValueError(f"not in the guess list: {', '.join(unknown)}")

    # One job per (opener, feedback group); the biggest go first since they take longest
    jobs = [(opener, code, S) for opener in openers
            for code, S in solver.groups(index[opener], solver.all_answers())]
    jobs.sort(key=lambda job: -len(job[2]))
    with Pool(processes, initializer=_init_worker,
              initargs=(solver.guesses, solver.answers, matrix_file, width)) as pool:
        solved = pool.map(_solve_job, jobs, chunksize=1)

    strategies = {}
    for opener in openers:
        tree = {"guess": opener, "map": {ALL_GREEN: opener} if opener in solver.answers else {}}
        strategies[opener] = Strategy(opener, len(answers), tree)
    for opener, code, cost, subtree in solved:
        strategies[opener].total_guesses += cost
        strategies[opener].tree["map"][code_to_pattern(code)] = subtree
    return sorted(strategies.values(), key=lambda s: s.total_guesses)


def rank_openers(guesses, answers, n: int) -> list[str]:
    """The n opening guesses that look most promising before any search."""
    solver = TreeSolver(guesses, answers, np.load(_cached_matrix(guesses, answers), mmap_mode="r"))
    score, _ = solver.scores(solver.all_answers())
    return [solver.guesses[g] for g in np.argsort(score, kind="stable")[:n]]


def _cached_matrix(guesses, answers):
    """Path to the feedback matrix for these word lists, computing it on first use.

    Worker processes memory-map the same file instead of each building a copy.
    """
    digest = hashlib.sha1("\n".join([*guesses, "", *answers]).encode()).hexdigest()[:12]
    path = CACHE_DIR / f"feedback_{digest}.npy"
    if not path.exists():
        CACHE_DIR.mkdir(exist_ok=True)
        partial = path.with_suffix(".partial.npy")
        np.save(partial, feedback_matrix(guesses, answers))
        partial.replace(path)
    return path


_worker = None


def _init_worker(guesses, answers, matrix_file, width):
    global _worker
    _worker = TreeSolver(guesses, answers, np.load(matrix_file, mmap_mode="r"), width)


def _solve_job(job):
    opener, code, S = job
    cost, _ = _worker.solve(S)
    return opener, code, cost, _worker.tree(S)
