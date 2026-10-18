"""Build a Wordle strategy (decision tree).

    python solve.py                          # leaderboard tree, opening with SALET
    python solve.py --live                   # the tree the bot plays with
    python solve.py --start salet crane      # try specific opening words
    python solve.py --top-starts 20          # also try the 20 most promising openers

Two trees can be built:

  default   The original 2,315 answers and 12,972 guesses, so results compare
            with other solvers. Writes words/leaderboard_tree.json and
            wordle_results/leaderboard.txt (each answer's guesses, one per line).
  --live    Also covers every answer NYT has used since, and allows every
            guess NYT accepts today. Writes words/live_tree.json.
"""
import argparse
import os
import time

from wordle.data import (CURRENT_GUESSES_FILE, LEADERBOARD_TREE_FILE, LIVE_TREE_FILE,
                         ORIGINAL_GUESSES_FILE, RESULTS_DIR, load_answers, load_guesses,
                         load_known_answers)
from wordle.search import rank_openers, solve_openers
from wordle.tree import play, save_tree

LEADERBOARD_FILE = RESULTS_DIR / "leaderboard.txt"


def display(path) -> str:
    """A path relative to the current folder when it's inside it."""
    relative = os.path.relpath(path)
    return str(path) if relative.startswith("..") else relative


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="build the tree the bot plays with")
    parser.add_argument("--start", nargs="+", metavar="WORD", default=[],
                        help="opening word(s) to try (default: salet, unless --top-starts is given)")
    parser.add_argument("--top-starts", type=int, default=0, metavar="N",
                        help="also try the N openers that look most promising before searching")
    parser.add_argument("--width", type=float, default=10.0,
                        help="search width: higher is slower but can find better trees (default: 10)")
    parser.add_argument("--out", help="where to write the tree (default depends on --live)")
    args = parser.parse_args()

    if args.live:
        answers, guesses = load_known_answers(), load_guesses(CURRENT_GUESSES_FILE)
        out = args.out or LIVE_TREE_FILE
    else:
        answers, guesses = load_answers(), load_guesses(ORIGINAL_GUESSES_FILE)
        out = args.out or LEADERBOARD_TREE_FILE

    openers = [w.lower() for w in args.start]
    unknown = [w for w in openers if w not in guesses]
    if unknown:
        parser.error(f"not in the guess list: {', '.join(unknown)}")

    started = time.time()
    if args.top_starts:
        openers += [w for w in rank_openers(guesses, answers, args.top_starts) if w not in openers]
    openers = openers or ["salet"]
    print(f"Searching {len(openers)} opener(s) with {len(guesses)} guesses and {len(answers)} answers...")
    strategies = solve_openers(guesses, answers, openers, width=args.width)
    elapsed = time.time() - started

    print(f"\n{'opener':<8}{'total':>7}{'average':>9}")
    for s in strategies:
        print(f"{s.opener.upper():<8}{s.total_guesses:>7}{s.total_guesses / len(answers):>9.4f}")

    # Double-check the winner by playing every answer through it
    best = strategies[0]
    games = {answer: play(best.tree, answer) for answer in answers}
    lengths = [len(g) for g in games.values()]
    assert sum(lengths) == best.total_guesses
    distribution = {n: lengths.count(n) for n in sorted(set(lengths))}
    average = best.total_guesses / len(answers)

    save_tree(out, best.tree, answers, opener=best.opener, total_guesses=best.total_guesses,
              average=round(average, 4), max_guesses=max(lengths), width=args.width, seconds=round(elapsed, 1))
    written = [out]
    if not args.live:
        RESULTS_DIR.mkdir(exist_ok=True)
        with open(LEADERBOARD_FILE, "w") as f:
            f.writelines(",".join(games[answer]) + "\n" for answer in answers)
        written.append(LEADERBOARD_FILE)

    print(f"\nBest: {best.opener.upper()}  average {average:.4f}, at most {max(lengths)} guesses, "
          f"distribution {distribution}")
    print(f"Computation time: {elapsed:.1f}s")
    print(f"Wrote {' and '.join(display(p) for p in written)}")


if __name__ == "__main__":
    main()
