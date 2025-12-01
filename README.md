# Wordle Optimizer

An intelligent Wordle solver that leverages information theory, entropy calculations, and optimization algorithms to solve Wordle puzzles with maximum efficiency. This project demonstrates advanced data science techniques including probability theory, statistical analysis, and algorithmic optimization.

## Overview

This project implements a data-driven approach to solving Wordle puzzles by:
- **Information Theory**: Using entropy calculations to maximize information gain with each guess
- **Optimization Algorithms**: Combining multiple scoring strategies (entropy, minimax, pattern matching)
- **Statistical Analysis**: Analyzing letter frequencies, position probabilities, and pattern distributions
- **Performance Optimization**: Parallel processing and caching for efficient computation

## Key Features

- **Entropy-Based Word Selection**: Calculates information gain (in bits) for each possible guess using Shannon entropy
- **Multi-Strategy Optimization**: Combines entropy (40%), pattern matching (20%), position scoring (20%), minimax (10%), and pattern sequence analysis (10%)
- **MIT Research Integration**: Uses proven optimal starting word (SALET) based on MIT research
- **Parallel Processing**: Multiprocessing implementation for fast entropy calculations across large word sets
- **Pattern Caching**: Optimized pattern matching with caching for improved performance
- **Automated Gameplay**: Selenium-based automation for playing Wordle on NYT website
- **Comprehensive Logging**: Detailed game analysis with technical explanations and statistics

## Project Structure

```
wordle_optimizer/
├── automated_wordle.py          # Main automation script using Selenium
├── bots/
│   ├── wordle_optimizer.py      # Core optimization engine with entropy calculations
│   └── entropy_wordle_optimizer.py  # Alternative entropy-based implementation
├── words/
│   ├── answers.txt              # List of possible Wordle answers (2,315 words)
│   └── words.txt                # List of all valid guesses (14,856 words)
├── wordle_results/
│   ├── screenshots/             # Game screenshots organized by date
│   └── wordle_log.txt           # Detailed game logs and analysis
└── requirements.txt             # Python dependencies
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd wordle_optimizer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure word lists are present:**
   - `words/answers.txt` - Contains possible Wordle answers (2,315 words)
   - `words/words.txt` - Contains all valid guesses (14,856 words)

## Usage

### Automated Play

Run the automated Wordle solver:

```bash
python automated_wordle.py
```

The script will:
- Launch a headless Chrome browser
- Navigate to the NYT Wordle website
- Automatically play the daily puzzle using optimal strategies
- Save screenshots and detailed logs with analysis

### Interactive Mode

Use the optimizer interactively for manual play:

```bash
python bots/wordle_optimizer.py
```

This allows you to:
- Get word suggestions based on your guesses
- Enter patterns manually (2=green, 1=yellow, 0=gray)
- See remaining possible answers
- Track game statistics

## Algorithm & Methodology

### Information Theory Foundation

The core of this optimizer is based on **Shannon entropy** from information theory. For each possible guess, we calculate the expected information gain:

```
H(guess) = -Σ P(pattern) × log₂(P(pattern))
```

Where:
- `P(pattern)` is the probability of each possible pattern outcome
- Higher entropy means more information gain
- The goal is to maximize entropy to minimize expected number of guesses

### Optimization Strategy

The `WordleOptimizer` uses a multi-layered approach:

1. **First Guess**: Uses "SALET" - proven optimal starting word (MIT research, average 1.683 colored tiles)

2. **Second Guess**: Prioritizes words that:
   - Eliminate multiple possibilities simultaneously
   - Use different letters from the first guess
   - Maximize pattern diversity

3. **Later Guesses**: Combines multiple scoring factors:
   - **Entropy (40%)**: Information gain measured in bits
   - **Pattern Matching (20%)**: How well the word complements previous guesses
   - **Position Scoring (20%)**: Letter frequency at each position in remaining words
   - **Minimax (10%)**: Worst-case scenario optimization
   - **Pattern Sequence (10%)**: Historical pattern analysis

### Pattern Matching Algorithm

The system uses a three-state pattern encoding:
- `2` = Green (correct letter, correct position)
- `1` = Yellow (correct letter, wrong position)
- `0` = Gray (letter not in word)

Pattern matching is optimized with:
- **Caching**: Pre-computed pattern lookups for faster filtering
- **Early Exit**: Optimized filtering for common patterns (all gray, all green)
- **Multiprocessing**: Parallel entropy calculations across CPU cores

### Word Filtering

After each guess, the system filters possible answers by:
1. Checking if the pattern matches for each candidate answer
2. Maintaining constraints from previous guesses
3. Handling edge cases (all gray, all green patterns)
4. Using set operations for efficient filtering

## Performance Optimizations

- **Multiprocessing**: Entropy calculations parallelized across CPU cores using Python's `multiprocessing.Pool`
- **Pattern Caching**: Cached pattern calculations (`pattern_cache`) for O(1) lookups
- **Early Exit Strategies**: Optimized filtering for common patterns
- **Set Operations**: Efficient word filtering using Python sets
- **Normalized Scoring**: Score normalization for fair combination of different metrics

## Output & Analysis

### Screenshots

Screenshots are saved in `wordle_results/screenshots/YYYYMMDD/`:
- `initial.png` - Initial game state
- `guess_N.png` - After each guess
- `final.png` - Final game state

### Logs

Detailed logs are written to `wordle_results/wordle_log.txt`:
- Technical explanations of strategy
- Simple explanations for each guess
- Pattern analysis and elimination statistics
- Game progression summaries
- Final game analysis with efficiency metrics

## Technical Details

### Dependencies

- `selenium` - Web automation for playing Wordle
- `numpy` - Numerical calculations for entropy (log₂ operations)
- `schedule` - Task scheduling for automated daily runs
- `webdriver-manager` - ChromeDriver management
- `pandas` - Data processing (for frequency analysis in alternative implementation)

### Computational Complexity

- **Pattern Generation**: O(n) where n is word length (5)
- **Entropy Calculation**: O(m × n) where m is number of possible answers, n is word length
- **Word Filtering**: O(m) where m is number of possible answers
- **Best Word Selection**: O(k × m × n) where k is number of candidate words, optimized with multiprocessing

### Data Structures

- **Sets**: For efficient word filtering and lookups
- **DefaultDict**: For pattern counting and frequency analysis
- **LRU Cache**: For pattern caching (via `@lru_cache` decorator)
- **Dictionaries**: For scoring weights and normalization

## Research & References

This project is based on research from MIT on optimal Wordle strategies. The entropy-based approach follows information theory principles to maximize information gain with each guess, similar to strategies used in optimal decision-making under uncertainty.

Key concepts:
- **Shannon Entropy**: Measure of information content
- **Information Gain**: Expected reduction in uncertainty
- **Minimax Strategy**: Optimizing for worst-case scenarios
- **Pattern Analysis**: Statistical analysis of feedback patterns

## Results & Performance

The optimizer was tested against **1,355 historical Wordle answers** to validate its effectiveness. The results demonstrate the power of the entropy-based optimization approach:

### Overall Performance

- **Total Games**: 1,355
- **Wins**: 1,332
- **Win Rate**: **98.30%**
- **Average Guesses (for wins)**: **3.57**
- **Processing Time**: 307.91 seconds (~5 minutes) for all 1,355 games
- **Processing Rate**: 4.40 games/second

### Guess Distribution

The optimizer demonstrates strong performance with most games solved in 3-4 guesses:

| Guesses | Games | Percentage |
|---------|-------|------------|
| 1 guess | 0 | 0.0% |
| 2 guesses | 77 | 5.8% |
| 3 guesses | 575 | **43.2%** |
| 4 guesses | 543 | **40.8%** |
| 5 guesses | 118 | 8.9% |
| 6 guesses | 19 | 1.4% |

**Key Insights:**
- **84.0%** of successful games are solved in 3-4 guesses
- The distribution shows a strong peak around 3-4 guesses, indicating consistent performance
- Only 1.4% of games require the full 6 guesses

### Challenging Words

**Words that required 6 guesses (19 words):**
hatch, carry, riper, moose, joker, scout, froze, magma, bunch, state, rover, shape, brown, boxer, rower, score, greed, baste, pitch

**Words that failed to solve (23 words, 1.7% failure rate):**
shake, watch, foyer, sever, patty, taunt, guano, snafu, balsa, kazoo, taste, laser, pious, beaut, mommy, primp, uvula, atlas, squid, indie, spate, suede, grift

### Analysis

The **98.30% win rate** and **3.57 average guesses** demonstrate the effectiveness of the entropy-based optimization strategy. The system efficiently narrows down from 2,315 possible answers to the correct solution through systematic information maximization. The failure cases (1.7%) typically involve words with unusual letter combinations or patterns that require more strategic exploration than the 6-guess limit allows.

## Limitations

While the optimizer achieves strong performance, there are several limitations to consider:

### Algorithmic Limitations

- **Fixed Strategy Weights**: The scoring weights (40% entropy, 20% pattern matching, etc.) are manually tuned and may not be optimal for all game states. A dynamic weighting system could potentially improve performance.

- **Limited Lookahead**: The current implementation uses a greedy approach, selecting the best word for the current state without considering future moves. A minimax approach with deeper lookahead could improve performance on challenging words.

- **Pattern Sequence Analysis**: The pattern sequence scoring (10% weight) is relatively simple and could be enhanced with more sophisticated pattern recognition and learning from historical games.

### Performance Limitations

- **Computational Cost**: Entropy calculations for all possible guesses can be computationally expensive, especially in early game states with many remaining possibilities. While multiprocessing helps, there's room for further optimization.

- **Memory Usage**: Pattern caching and storing all possible words in memory can be memory-intensive for large word sets.

### Failure Cases

- **Unusual Letter Combinations**: Words with rare letter patterns (e.g., "uvula", "kazoo", "snafu") can be challenging because they don't follow common English letter frequency patterns.

- **Ambiguous Patterns**: Some words share similar patterns with many other words, making it difficult to distinguish them within 6 guesses (e.g., "shake", "spate", "taste" all share similar letter combinations).

- **Hard Mode Constraints**: The current implementation doesn't strictly enforce "hard mode" rules (where revealed letters must be used in subsequent guesses), which could limit optimization in some scenarios.

### Data Limitations

- **Static Word Lists**: The word lists are static and don't adapt to changes in the official Wordle answer list over time.

- **No Learning Component**: The system doesn't learn from past games or adapt its strategy based on historical performance patterns.

## Next Steps

Future improvements and enhancements planned for this project:

### Algorithm Enhancements

- **Dynamic Weight Tuning**: Implement machine learning techniques to automatically optimize the scoring weights based on game outcomes, potentially using reinforcement learning or genetic algorithms.

- **Deep Lookahead**: Implement a minimax algorithm with configurable depth to consider multiple moves ahead, especially useful for challenging words that require strategic planning.

- **Adaptive Strategy Selection**: Develop a system that dynamically selects different strategies based on game state (e.g., use minimax when few words remain, use entropy when many words remain).

### Performance Improvements

- **GPU Acceleration**: Explore using GPU computing (e.g., CuPy or PyTorch) to parallelize entropy calculations for even faster processing.

- **Incremental Caching**: Implement more sophisticated caching strategies that persist across games and sessions to reduce redundant calculations.

- **Early Termination**: Add heuristics to identify when a solution is guaranteed and skip unnecessary calculations.

### Feature Additions

- **Hard Mode Support**: Implement strict hard mode enforcement where revealed letters must be used in subsequent guesses.

- **Learning Component**: Add a machine learning component that learns from historical games to improve word selection, potentially using neural networks or decision trees.

- **Real-time Visualization**: Create interactive visualizations showing entropy calculations, word elimination process, and decision trees for each game.

- **Comparative Analysis**: Build tools to compare different optimization strategies (pure entropy vs. minimax vs. hybrid approaches) on the same word sets.

### Research & Analysis

- **Failure Case Analysis**: Conduct deeper analysis of the 23 failed words to identify common patterns and develop targeted strategies.

- **Optimal Starting Word Research**: Explore alternatives to SALET and test their performance across different word sets.

- **Pattern Recognition**: Develop more sophisticated pattern recognition algorithms that can identify common Wordle patterns and exploit them.

- **Statistical Modeling**: Create predictive models that estimate the probability of solving a word within N guesses based on its characteristics.

### Infrastructure

- **Testing Framework**: Expand the testing framework to include more comprehensive benchmarks, A/B testing of different strategies, and automated regression testing.

- **Documentation**: Enhance documentation with detailed algorithm explanations, mathematical proofs, and performance analysis.

- **Modular Architecture**: Refactor the codebase to be more modular, allowing easy swapping of different optimization strategies and scoring functions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
