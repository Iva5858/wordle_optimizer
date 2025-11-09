# Wordle Optimizer

An automated Wordle solver that uses information theory and entropy calculations to play the daily NYT Wordle puzzle. The system combines Selenium-based web automation with advanced optimization algorithms to achieve optimal gameplay.

## Features

- **Automated Gameplay**: Uses Selenium WebDriver to automatically play Wordle on the NYT website
- **Information Theory-Based Optimization**: Implements entropy calculations to maximize information gain with each guess
- **MIT Research Strategies**: Uses proven optimal starting words (SALET) based on MIT research
- **Multi-Strategy Scoring**: Combines entropy, pattern matching, position scoring, and minimax strategies
- **Detailed Logging**: Comprehensive game analysis with technical and simple explanations
- **Screenshot Capture**: Automatically captures screenshots of each guess and final results
- **Scheduled Execution**: Can be configured to run daily at specified times
- **Historical Data**: Utility to fetch past Wordle answers from NYT API

## Project Structure

```
Wordle-opt/
├── automated_wordle.py          # Main automation script using Selenium
├── bots/
│   └── wordle_optimizer.py      # Core optimization engine with entropy calculations
├── get_wordle_answers.py        # Utility to fetch historical Wordle answers
├── words/
│   ├── answers.txt              # List of possible Wordle answers (2,315 words)
│   ├── words.txt                # List of all valid guesses (10,657 words)
│   └── past_answers.txt         # Historical answers from NYT API
├── wordle_results/
│   ├── screenshots/             # Game screenshots organized by date
│   └── wordle_log.txt           # Detailed game logs and analysis
└── requirements.txt             # Python dependencies
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Wordle-opt
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure word lists are present:**
   - `words/answers.txt` - Contains possible Wordle answers
   - `words/words.txt` - Contains all valid guesses

## Usage

### Automated Play

Run the automated Wordle solver:

```bash
python automated_wordle.py
```

The script will:
- Launch a headless Chrome browser
- Navigate to the NYT Wordle website
- Accept cookies and terms
- Automatically play the daily puzzle using optimal strategies
- Save screenshots and detailed logs

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

### Scheduled Daily Execution

The script can be configured to run automatically:

```python
# In automated_wordle.py, modify the schedule:
schedule.every().day.at("00:00").do(run_daily_wordle)
```

### Fetch Historical Answers

Get past Wordle answers from the NYT API:

```bash
python get_wordle_answers.py
```

This will fetch all historical answers and save them to `words/past_answers.txt`.

## How It Works

### Optimization Strategy

The `WordleOptimizer` uses a multi-layered approach:

1. **First Guess**: Uses "SALET" - proven optimal starting word (MIT research)
2. **Second Guess**: Prioritizes words that eliminate multiple possibilities and use different letters
3. **Later Guesses**: Combines multiple scoring factors:
   - **Entropy** (40%): Information gain measured in bits
   - **Pattern Matching** (20%): How well the word complements previous guesses
   - **Position Scoring** (20%): Letter frequency at each position
   - **Minimax** (10%): Worst-case scenario optimization
   - **Pattern Sequence** (10%): Historical pattern analysis

### Pattern Matching

The system uses a three-state pattern:
- `2` = Green (correct letter, correct position)
- `1` = Yellow (correct letter, wrong position)
- `0` = Gray (letter not in word)

### Performance Optimizations

- **Multiprocessing**: Entropy calculations parallelized across CPU cores
- **Pattern Caching**: Cached pattern calculations for faster lookups
- **Early Exit Strategies**: Optimized filtering for common patterns (all gray, all green)

## Output

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
- Final game analysis

## Dependencies

- `selenium` - Web automation
- `numpy` - Numerical calculations for entropy
- `schedule` - Task scheduling
- `webdriver-manager` - ChromeDriver management
- `requests` - API requests for historical data
- `pandas` - Data processing (for frequency analysis)

## Algorithm Details

### Entropy Calculation

The entropy of a guess is calculated as:

```
H(guess) = -Σ P(pattern) × log₂(P(pattern))
```

Where `P(pattern)` is the probability of each possible pattern outcome. Higher entropy means more information gain.

### Word Filtering

After each guess, the system filters possible answers by:
1. Checking if the pattern matches for each candidate answer
2. Maintaining constraints from previous guesses
3. Handling edge cases (all gray, all green patterns)

## Credits

Based on research from MIT on optimal Wordle strategies. The entropy-based approach follows information theory principles to maximize information gain with each guess.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
