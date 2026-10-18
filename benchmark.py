"""Play a list of answers through the bot and report how it does.

    python benchmark.py                                  # every real NYT answer so far
    python benchmark.py --words words/current_guesses.txt   # every word NYT could ever pick
    python benchmark.py --tree words/leaderboard_tree.json
"""
import argparse
import time
from collections import Counter
from multiprocessing import Pool

from wordle.data import CURRENT_GUESSES_FILE, LIVE_TREE_FILE, PAST_ANSWERS_FILE, load_guesses, load_words
from wordle.feedback import feedback
from wordle.player import MAX_GUESSES, Player
from wordle.tree import load_tree

_game = None  # (tree, answers, guesses), loaded once per worker process


def _load(tree_file):
    global _game
    _game = (*load_tree(tree_file), load_guesses(CURRENT_GUESSES_FILE))


def play_game(answer: str):
    """Return the number of guesses the bot needs, or None if it runs out."""
    player = Player(*_game)
    for turn in range(1, MAX_GUESSES + 1):
        guess = player.next_guess()
        player.record(guess, feedback(guess, answer))
        if player.solved:
            return turn
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--words", default=PAST_ANSWERS_FILE, help="answers to play (default: past NYT answers)")
    parser.add_argument("--tree", default=LIVE_TREE_FILE, help="strategy to play (default: the live tree)")
    args = parser.parse_args()

    targets = load_words(args.words)
    known = set(load_tree(args.tree)[1])
    started = time.time()
    with Pool(initializer=_load, initargs=(args.tree,)) as pool:
        results = dict(zip(targets, pool.map(play_game, targets, chunksize=8)))

    solved = [n for n in results.values() if n]
    losses = [w for w, n in results.items() if n is None]
    unknown = [w for w in targets if w not in known]
    print(f"Played {len(targets)} games in {time.time() - started:.1f}s")
    print(f"Average guesses: {sum(solved) / len(solved):.4f}")
    print(f"Distribution: {dict(sorted(Counter(solved).items()))}")
    print(f"Losses: {len(losses)}" + (f" ({', '.join(losses)})" if losses else ""))
    if unknown:
        print(f"{len(unknown)} of these aren't in the tree's answer list; "
              f"they took {sum(results[w] or MAX_GUESSES + 1 for w in unknown) / len(unknown):.2f} guesses on average")


if __name__ == "__main__":
    main()
