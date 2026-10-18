# Wordle Optimizer

A Wordle solver that searches for the strategy needing the fewest guesses, and
a bot that uses it to play the daily New York Times puzzle in Chrome.

On the original 2,315-answer list it averages **3.4212 guesses**, never needs
more than 5, and never loses. That matches the best average known to be
possible when opening with SALET. Finding the strategy takes about 6 seconds.

| | Games | Average | Distribution (2 / 3 / 4 / 5 / 6) | Losses |
|---|---|---|---|---|
| Original answer list | 2,315 | **3.4212** | 78 / 1,225 / 971 / 41 / 0 | 0 |
| Every real NYT answer through Oct 2026 | 1,920 | 3.4593 | 58 / 992 / 803 / 59 / 6 | 2 |

The real NYT answers include 69 words added after the original list. The bot
handles those live (see [Playing a real game](#playing-a-real-game)), but they
cost more guesses, and two of them (GOFER and MOMMY) were lost.

## Quick start

```bash
git clone https://github.com/Iva5858/wordle_optimizer.git
cd wordle_optimizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python automated_wordle.py      # play today's Wordle (needs Google Chrome)
python assistant.py             # get suggestions while you play yourself
```

The strategy (`words/solver_tree.json`) ships with the repo, so nothing needs
to be computed first.

## Scripts

### `solve.py`: build the strategy

```bash
python solve.py                               # open with SALET (default)
python solve.py --start salet crane trace     # compare specific openers
python solve.py --top-starts 20               # try the 20 most promising openers
python solve.py --start salet --top-starts 10 --width 3
```

All the openers are searched in parallel and the best one is kept. It writes:

- `words/solver_tree.json`: the decision tree the bot plays from
- `wordle_results/leaderboard.txt`: every guess for each answer, one line per
  answer (`salet,brond,aback`), in the format Wordle bot leaderboards accept

| Option | Default | |
|---|---|---|
| `--start WORD ...` | `salet` | opening words to try |
| `--top-starts N` | 0 | also try the N openers that look best before searching |
| `--width W` | 10 | how many guesses to consider at each step; higher is slower but can find better trees |
| `--guesses FILE` | `words/original_guesses.txt` | allowed guesses |

### `automated_wordle.py`: play the NYT puzzle

```bash
python automated_wordle.py                 # play once now
python automated_wordle.py --daily 00:05   # keep running, play every day at 00:05
python automated_wordle.py --show          # watch it play instead of running headless
```

It clicks through the welcome screen, ads and popups, plays the game, and saves
a screenshot of the board after each guess to `wordle_results/screenshots/`.
Each game is appended to `wordle_results/wordle_log.txt`:

```
2026-10-18 00:00
  1. SALET  01000  2315 -> 102 possible
  2. BROND  01211  102 -> 1 possible
  3. ADORN  22222  1 -> 1 possible
  Solved in 3
```

Selenium downloads the matching chromedriver automatically; you only need
Chrome installed.

### `assistant.py`: help while you play

Suggests a word, then asks which word you played and the colors you got
(`2` green, `1` yellow, `0` gray), and lists the remaining answers once there
are 10 or fewer.

### `benchmark.py`: measure the bot

```bash
python benchmark.py                          # every real NYT answer so far
python benchmark.py --words words/answers.txt
```

### `fetch_past_answers.py`: update the real answers

Downloads every NYT answer since the first Wordle into `words/past_answers.txt`.

## How it works

### The cost of a strategy

A strategy is a decision tree: a first guess, then for every possible color
pattern, the next guess. Its quality is the total number of guesses it needs
across all answers (the average is that total divided by 2,315).

For a set *S* of answers that are still possible, choosing guess *g* costs

```
cost(S, g) = |S| + Σ cost(B)   for each group B of S that g doesn't solve
```

Every answer in *S* spends this guess. The guess then splits *S* into groups
by the colors it would get, and each group continues in its own subtree. The
solver looks for the guess, at every node, that minimizes this cost.

### Making the search fast

Trying every guess at every node is far too slow (12,972 guesses, nested
several levels deep), so `wordle/search.py` uses:

- **A precomputed feedback matrix.** The colors for every guess against every
  answer (30 million pairs) are computed once with numpy, in about a second,
  and cached in `.cache/`.
- **Exact shortcuts.** If a guess splits the remaining answers into single
  words, no strategy can do better, so the search stops there.
- **A beam.** Guesses are ranked by how small the groups they leave are, and
  only the best few are searched (more when more answers remain). `--width`
  scales this.
- **Branch and bound.** Each group of *n* answers needs at least 2*n* − 1
  guesses. A candidate is dropped as soon as its cost so far plus those lower
  bounds can't beat the best guess found.
- **Memoization and parallelism.** Solved groups are cached, and the subtrees
  under the first guess are solved on all CPU cores.

The tests check the result against a brute-force search that tries every
guess at every node, on small word sets where that's feasible.

### Choosing an opener

`--top-starts` ranks openers by the same "smallest groups" score used inside
the search. That ranking isn't the whole story. The words it likes best leave
groups that are harder to finish, and SALET wins once everything is searched:

| Opener | Total | Average |
|---|---|---|
| **SALET** | **7,920** | **3.4212** |
| SOARE | 7,997 | 3.4544 |
| ROATE | 8,000 | 3.4557 |
| RAINE | 8,003 | 3.4570 |
| RAISE | 8,015 | 3.4622 |
| ARISE | 8,043 | 3.4743 |

(`python solve.py --start salet --top-starts 10`, 42 seconds.)

### Playing a real game

`wordle/player.py` follows the tree while the game stays on it. NYT has since
added answers that aren't in the original list. When the colors rule out every
original answer, the player switches to all currently allowed words that still
fit, and runs the same search on those, live.

## Word lists

| File | Words | |
|---|---|---|
| `words/answers.txt` | 2,315 | the original answer list |
| `words/original_guesses.txt` | 10,657 | the original list of other allowed guesses (from [cfreshman's gist](https://gist.github.com/cfreshman/cdcdf777450c5b5301e439061d29694c)) |
| `words/current_guesses.txt` | 14,855 | every guess NYT accepts today |
| `words/past_answers.txt` | 1,947 | real NYT answers, in order |

The strategy uses only the original lists, so its results can be compared with
other solvers and submitted to leaderboards. Allowing the newer guesses as well
(`--guesses words/current_guesses.txt`) gets the average down to 3.4199, but
uses words other solvers and leaderboards don't accept.

## Project structure

```
wordle_optimizer/
├── solve.py                  # build the strategy
├── automated_wordle.py       # play the NYT puzzle in Chrome
├── assistant.py              # suggestions while you play
├── benchmark.py              # measure the bot on a list of answers
├── fetch_past_answers.py     # download real NYT answers
├── wordle/
│   ├── feedback.py           # the colors a guess gets, one at a time or as a matrix
│   ├── search.py             # the tree search
│   ├── tree.py               # saving, loading and following trees
│   ├── player.py             # picking guesses during a live game
│   └── data.py               # word lists and file locations
├── words/                    # word lists and the solved tree
└── tests/
```

## Tests

```bash
python -m pytest
```

## Limitations

- **Newer NYT answers.** The tree only covers the original 2,315 answers, so
  newer ones cost extra guesses. Including `past_answers.txt` in the answer
  list the tree is built for would fix most of this.
- **The opener is chosen, not proven.** The search is exhaustive enough to
  match the best known result for SALET, but with a limited beam it can't prove
  no tree does better.
- **Hard mode** (reusing every revealed letter) isn't supported.
- **NYT page changes.** The bot finds the board and buttons by their current
  HTML. If NYT redesigns the page, the selectors at the top of
  `automated_wordle.py` need updating.

## Acknowledgements

The best average for a SALET opener, 3.4212, was established by
[Jonathan Olson](https://jonathanolson.net/experiments/optimal-wordle-solutions).
This project's search was written independently and reaches the same total.

## License

MIT, see [LICENSE](LICENSE).
