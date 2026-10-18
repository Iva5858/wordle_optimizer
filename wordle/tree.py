"""Saving, loading and following the decision trees the solver produces.

A node is {"guess": word, "map": {feedback: child}}, and a child that is a
plain word means "guess this, it's the answer".
"""
import json

from .feedback import ALL_GREEN, feedback


def guess_at(node) -> str:
    return node if isinstance(node, str) else node["guess"]


def follow(node, pattern: str):
    """The subtree reached after getting `pattern`, or None if the tree doesn't cover it."""
    if isinstance(node, str) or pattern == ALL_GREEN:
        return None
    return node["map"].get(pattern)


def play(tree, answer: str) -> list[str]:
    """Every guess the tree makes for `answer`, ending with the answer itself."""
    node, guesses = tree, []
    while node is not None:
        guesses.append(guess_at(node))
        pattern = feedback(guesses[-1], answer)
        if pattern == ALL_GREEN:
            return guesses
        node = follow(node, pattern)
    raise ValueError(f"the tree doesn't cover {answer!r}")


def save_tree(path, tree, answers, **info):
    """Save a tree together with the answers it was built for, plus any extra info."""
    with open(path, "w") as f:
        json.dump({**info, "answers": answers, "tree": tree}, f, separators=(",", ":"))


def load_tree(path):
    """Return (tree, answers it covers)."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"{path} not found; build it with solve.py (see README)") from None
    return data["tree"], data["answers"]
