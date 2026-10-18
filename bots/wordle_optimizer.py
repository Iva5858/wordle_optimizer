import numpy as np
from collections import defaultdict
from typing import List, Tuple, Set, Dict
import json
import os
from multiprocessing import Pool, cpu_count
from functools import lru_cache
import itertools

# ANSI color codes for terminal output
COLORS = {
    'green': '\033[92m',
    'yellow': '\033[93m',
    'gray': '\033[90m',
    'reset': '\033[0m',
    'bold': '\033[1m'
}

def colorize_pattern(word: str, pattern: str) -> str:
    """Return a colored string representation of a word with its pattern."""
    result = ""
    for letter, code in zip(word.upper(), pattern):
        if code == '2':
            result += f"{COLORS['green']}{letter}{COLORS['reset']}"
        elif code == '1':
            result += f"{COLORS['yellow']}{letter}{COLORS['reset']}"
        else:
            result += f"{COLORS['gray']}{letter}{COLORS['reset']}"
    return result

def print_suggestion(word: str, score: float, description: str = "") -> None:
    """Print a word suggestion with formatting."""
    print(f"{COLORS['bold']}{word.upper()}{COLORS['reset']} "
          f"({score:.2f} bits) {description}")

# Best starting words with their explanations and strategies
BEST_STARTING_WORDS = [
    ("SALET", "Best first word - reveals avg 1.683 colored tiles (MIT research)")
]

def nested_dict():
    """Helper function to create nested defaultdict."""
    return defaultdict(list)

class WordleOptimizer:
    def __init__(self, word_list_file: str = "words/words.txt", answers_file: str = "words/answers.txt",
                 tree_file: str = "words/salet_tree.json"):
        """Initialize the Wordle optimizer with word lists.
        
        Args:
            word_list_file: File containing all valid guesses (10,657 words)
            answers_file: File containing possible answers (2,315 words)
        """
        # Load all valid guesses
        with open(word_list_file, 'r') as f:
            self.all_words = {word.strip().lower() for word in f.readlines()}
        
        # Load possible answers (subset of all words)
        try:
            with open(answers_file, 'r') as f:
                self.possible_answers = {word.strip().lower() for word in f.readlines()}
        except FileNotFoundError:
            # If no answers file provided, use all words as possible answers
            self.possible_answers = self.all_words.copy()
            
        print(f"Loaded {len(self.all_words)} valid guesses and {len(self.possible_answers)} possible answers")
        
        self.word_length = 5
        self.max_attempts = 6
        self.pattern_cache = {}
        self.current_guess_number = 1
        
        # Game statistics
        self.game_history = []
        self.current_game = {
            'guesses': [],
            'patterns': [],
            'remaining_words': []
        }
        
        # Precomputed optimal decision tree (see words/salet_tree.json for its source).
        # We follow it while the game stays on it, and fall back to heuristics otherwise.
        self.tree = None
        if tree_file and os.path.exists(tree_file):
            with open(tree_file, 'r') as f:
                self.tree = json.load(f)['tree']
        self.tree_node = self.tree

        # Pre-calculate letter positions for faster pattern matching
        self.letter_positions = defaultdict(nested_dict)
        for word in self.all_words:
            for i, letter in enumerate(word):
                self.letter_positions[word][letter].append(i)

    def get_pattern(self, guess: str, answer: str) -> str:
        """
        Generate the pattern for a guess compared to the answer.
        Returns a string of:
        '2' - green (correct letter, correct position)
        '1' - yellow (correct letter, wrong position)
        '0' - gray (letter not in word)
        """
        # Check cache first
        cache_key = (guess, answer)
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        pattern = ['0'] * self.word_length
        remaining_letters = defaultdict(int)
        
        # Count remaining letters in answer
        for letter in answer:
            remaining_letters[letter] += 1

        # First pass: mark correct positions (green)
        for i, (g, a) in enumerate(zip(guess, answer)):
            if g == a:
                pattern[i] = '2'
                remaining_letters[g] -= 1

        # Second pass: mark correct letters in wrong positions (yellow)
        for i, (g, a) in enumerate(zip(guess, answer)):
            if pattern[i] != '2' and remaining_letters[g] > 0:
                pattern[i] = '1'
                remaining_letters[g] -= 1

        result = ''.join(pattern)
        self.pattern_cache[cache_key] = result
        return result

    def filter_words(self, guess: str, pattern: str) -> None:
        """Filter the possible answers based on the guess and its pattern."""
        print(f"\nFiltering words with guess '{guess}' and pattern '{pattern}'")
        print(f"Before filtering: {len(self.possible_answers)} possible answers")
        
        # Quick check for all gray pattern
        if pattern == '00000':
            self.possible_answers = {
                word for word in self.possible_answers 
                if not any(letter in word for letter in guess)
            }
            print(f"After all-gray filter: {len(self.possible_answers)} possible answers")
            return

        # Quick check for all green pattern
        if pattern == '22222':
            self.possible_answers = {guess}
            print(f"After all-green filter: {len(self.possible_answers)} possible answers")
            return

        # Store original set for debugging
        original_answers = self.possible_answers.copy()
        
        self.possible_answers = {
            word for word in self.possible_answers
            if self.get_pattern(guess, word) == pattern
        }
        
        print(f"After pattern matching: {len(self.possible_answers)} possible answers")
        
        # If we filtered out all words, something might be wrong
        if not self.possible_answers:
            print("WARNING: All words were filtered out!")
            print("Original words:", sorted(list(original_answers))[:10], "...")
            # The answer isn't in our answer list: fall back to every valid word
            # that is still consistent with all the feedback received so far
            history = list(zip(self.current_game['guesses'], self.current_game['patterns'])) + [(guess, pattern)]
            self.possible_answers = {
                word for word in self.all_words
                if all(self.get_pattern(g, word) == p for g, p in history)
            }
            print(f"Falling back to all valid words consistent with feedback: {len(self.possible_answers)} words")

    def calculate_entropy(self, args) -> Tuple[str, float]:
        """Calculate entropy for a single word."""
        word, possible_answers = args
        pattern_counts = defaultdict(int)
        total = len(possible_answers)
        
        # Early exit if only a few possibilities remain
        if total <= 2:
            return (word, 0.0)
        
        # Count patterns
        for possible_answer in possible_answers:
            pattern = ['0'] * self.word_length
            remaining_letters = defaultdict(int)
            
            for letter in possible_answer:
                remaining_letters[letter] += 1

            for i, (g, a) in enumerate(zip(word, possible_answer)):
                if g == a:
                    pattern[i] = '2'
                    remaining_letters[g] -= 1

            for i, (g, a) in enumerate(zip(word, possible_answer)):
                if pattern[i] != '2' and remaining_letters[g] > 0:
                    pattern[i] = '1'
                    remaining_letters[g] -= 1

            pattern = ''.join(pattern)
            pattern_counts[pattern] += 1
        
        # Calculate entropy
        entropy = 0
        for count in pattern_counts.values():
            prob = count / total
            entropy -= prob * np.log2(prob)
            
        return (word, entropy)

    def calculate_pattern_weight(self, word: str, last_guess: str, last_pattern: str) -> float:
        """Calculate weight based on how well a word complements previous guesses."""
        # Avoid words that share letters with incorrect guesses
        weight = 1.0
        for i, (letter, pattern_code) in enumerate(zip(last_guess, last_pattern)):
            if pattern_code == '0' and letter in word:
                weight *= 0.8  # Penalize words containing gray letters
            elif pattern_code == '1' and letter == word[i]:
                weight *= 0.9  # Penalize words with yellow letters in same position
            elif pattern_code == '2' and letter != word[i]:
                weight *= 0.7  # Heavily penalize words that don't maintain green letters
        return weight

    def calculate_position_score(self, word: str) -> float:
        """Calculate score based on letter positions in remaining words."""
        score = 0
        for pos in range(self.word_length):
            pos_freq = defaultdict(int)
            for possible in self.possible_answers:
                pos_freq[possible[pos]] += 1
            
            # Add position-weighted score
            letter_freq = pos_freq.get(word[pos], 0)
            total_words = len(self.possible_answers)
            # Boost score if letter appears in more than half of remaining words
            weight = 1.5 if letter_freq > total_words/2 else 1.0
            score += letter_freq * weight
        
        return score

    def get_minimax_score(self, word: str) -> float:
        """Calculate minimax score for a word with few remaining possibilities."""
        if len(self.possible_answers) > 10:  # Only use for small sets
            return 0
            
        worst_case = 0
        for possible_answer in self.possible_answers:
            pattern = self.get_pattern(word, possible_answer)
            # Count how many words would remain after this guess
            remaining = sum(1 for w in self.possible_answers 
                          if self.get_pattern(word, w) == pattern)
            worst_case = max(worst_case, remaining)
        return -worst_case  # Negative because lower is better

    def get_pattern_sequence_score(self, word: str) -> float:
        """Score based on how often this word leads to quick solutions."""
        if len(self.current_game['patterns']) < 2:
            return 0
        
        # Get current pattern sequence
        pattern_sequence = ''.join(self.current_game['patterns'])
        
        # Simple scoring based on pattern analysis
        score = 0
        greens = pattern_sequence.count('2')
        yellows = pattern_sequence.count('1')
        
        # Reward words that match positions we're confident about
        for i, (letter, pattern_code) in enumerate(zip(word, pattern_sequence[-5:])):
            if pattern_code == '2':
                score += 2  # Heavily reward matching green positions
            elif pattern_code == '1' and letter in self.current_game['guesses'][-1]:
                score += 1  # Reward using yellow letters but in different positions
                
        return score * (1 + (greens + yellows * 0.5) / (len(pattern_sequence)))

    def get_best_words(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get the top n words with highest information gain.
        
        Uses an advanced strategy based on multiple scoring factors:
        1. For first guess, uses pre-computed optimal word SALET
        2. For second guess, prioritizes words that eliminate multiple possibilities at once
        3. For later guesses, combines entropy, pattern matching, position scoring, and minimax
        """
        print(f"\nGetting best words (attempt {self.current_guess_number})")
        print(f"Current possible answers: {len(self.possible_answers)}")

        # Follow the optimal decision tree while we're still on it
        if self.tree_node is not None:
            word = self.tree_node if isinstance(self.tree_node, str) else self.tree_node['guess']
            print(f"Using optimal decision tree: {word.upper()}")
            return [(word, 0.0)]
        
        # If we're on the first guess, return the predefined best word
        if self.current_guess_number == 1:
            word, desc = BEST_STARTING_WORDS[0]
            print(f"\nRecommended word {self.current_guess_number}: {word} ({desc})")
            return [(word.lower(), 0.0)]

        # If only a few words remain, return them sorted by minimax score
        if len(self.possible_answers) <= n:
            print(f"Few words remaining ({len(self.possible_answers)}), using minimax strategy")
            return [(word, self.get_minimax_score(word)) for word in sorted(self.possible_answers)]

        # For second guess, use MIT strategy of eliminating multiple possibilities
        if self.current_guess_number == 2:
            print("Using MIT strategy for second guess")
            first_word = BEST_STARTING_WORDS[0][0].lower()
            first_word_letters = set(first_word)
            
            # Calculate how many possibilities each word could eliminate
            elimination_scores = []
            for word in self.all_words:
                # Skip words that share too many letters with first guess
                if len(set(word) & first_word_letters) > 2:
                    continue
                    
                # Count how many remaining possibilities this word could distinguish
                patterns = set()
                for possible_answer in self.possible_answers:
                    patterns.add(self.get_pattern(word, possible_answer))
                
                # Score is based on number of unique patterns (more is better)
                # and number of non-overlapping letters with first guess
                unique_letters = len(set(word) - first_word_letters)
                elimination_score = len(patterns) * (1 + 0.1 * unique_letters)
                elimination_scores.append((word, elimination_score))
            
            # Sort by elimination score
            elimination_scores.sort(key=lambda x: x[1], reverse=True)
            print(f"Found {len(elimination_scores)} valid second-guess candidates")
            return elimination_scores[:n]

        # For later guesses, combine multiple scoring strategies
        print("Using entropy-based strategy for later guesses")
        args = [(word, self.possible_answers) for word in self.all_words]
        
        try:
            # Calculate entropy scores using multiprocessing
            with Pool(processes=cpu_count()) as pool:
                word_scores = pool.map(self.calculate_entropy, args)
            
            print(f"Calculated entropy scores for {len(word_scores)} words")
            
            # Get additional scoring factors
            pattern_weights = {}
            position_scores = {}
            minimax_scores = {}
            sequence_scores = {}
            
            # Only calculate these scores for top entropy candidates to save time
            top_candidates = sorted(word_scores, key=lambda x: x[1], reverse=True)[:n*2]
            print(f"Selected top {len(top_candidates)} candidates for additional scoring")
            
            for word, _ in top_candidates:
                if len(self.current_game['patterns']) > 0:
                    pattern_weights[word] = self.calculate_pattern_weight(
                        word, 
                        self.current_game['guesses'][-1],
                        self.current_game['patterns'][-1]
                    )
                else:
                    pattern_weights[word] = 1.0
                    
                position_scores[word] = self.calculate_position_score(word)
                minimax_scores[word] = self.get_minimax_score(word)
                sequence_scores[word] = self.get_pattern_sequence_score(word)

            # Normalize scores
            def normalize_scores(scores):
                if not scores:
                    return {}
                min_score = min(scores.values())
                max_score = max(scores.values())
                range_score = max_score - min_score
                if range_score == 0:
                    return {k: 1.0 for k in scores}
                return {k: (v - min_score) / range_score for k, v in scores.items()}

            norm_position = normalize_scores(position_scores)
            norm_minimax = normalize_scores(minimax_scores)
            norm_sequence = normalize_scores(sequence_scores)

            # Combine scores with weights
            final_scores = []
            for word, entropy in top_candidates:
                # Weight the different factors
                final_score = (
                    entropy * 0.4 +  # Entropy is still important
                    pattern_weights[word] * 0.2 +  # Pattern matching
                    norm_position[word] * 0.2 +    # Position scoring
                    norm_minimax[word] * 0.1 +     # Minimax for worst case
                    norm_sequence[word] * 0.1      # Pattern sequence history
                )
                final_scores.append((word, final_score))

            # Sort by final score and return top n
            final_scores.sort(key=lambda x: x[1], reverse=True)
            print(f"Found {len(final_scores)} valid suggestions")
            return final_scores[:n]
            
        except Exception as e:
            print(f"Error in get_best_words: {e}")
            # If something goes wrong, fall back to using all_words
            print("Falling back to using all_words")
            return [(word, 0.0) for word in sorted(self.all_words)[:n]]

    def make_guess(self, guess: str, pattern: str) -> None:
        """Update possible answers based on a guess and its feedback pattern."""
        self.filter_words(guess, pattern)
        self.advance_tree(guess, pattern)
        self.current_game['guesses'].append(guess)
        self.current_game['patterns'].append(pattern)
        self.current_game['remaining_words'].append(len(self.possible_answers))
        self.current_guess_number += 1

    def advance_tree(self, guess: str, pattern: str) -> None:
        """Move to the tree node for this feedback, or leave the tree if the game has gone off it."""
        node = self.tree_node
        if node is None or isinstance(node, str) or node['guess'] != guess:
            self.tree_node = None
            return
        self.tree_node = node['map'].get(pattern)
        if self.tree_node is None:
            print("Feedback not in decision tree (answer may be outside the original list); using heuristics")

    def save_game(self, won: bool) -> None:
        """Save the current game statistics."""
        self.current_game['won'] = won
        self.current_game['num_guesses'] = len(self.current_game['guesses'])
        self.game_history.append(self.current_game)
        self.tree_node = self.tree
        self.current_game = {
            'guesses': [],
            'patterns': [],
            'remaining_words': []
        }

    def get_statistics(self) -> Dict:
        """Return game statistics."""
        if not self.game_history:
            return {}
        
        total_games = len(self.game_history)
        games_won = sum(1 for game in self.game_history if game['won'])
        avg_guesses = sum(game['num_guesses'] for game in self.game_history) / total_games
        
        guess_distribution = defaultdict(int)
        for game in self.game_history:
            if game['won']:
                guess_distribution[game['num_guesses']] += 1
        
        return {
            'total_games': total_games,
            'games_won': games_won,
            'win_rate': games_won / total_games * 100,
            'average_guesses': avg_guesses,
            'guess_distribution': dict(guess_distribution)
        }

    def print_statistics(self) -> None:
        """Print game statistics in a formatted way."""
        stats = self.get_statistics()
        if not stats:
            print(f"{COLORS['yellow']}No games played yet!{COLORS['reset']}")
            return
        
        print(f"\n{COLORS['bold']}Game Statistics:{COLORS['reset']}")
        print(f"Games Played: {stats['total_games']}")
        print(f"Games Won: {stats['games_won']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Average Guesses: {stats['average_guesses']:.1f}")
        
        print(f"\n{COLORS['bold']}Guess Distribution:{COLORS['reset']}")
        max_count = max(stats['guess_distribution'].values(), default=0)
        for guesses in range(1, self.max_attempts + 1):
            count = stats['guess_distribution'].get(guesses, 0)
            bar_length = int(20 * count / max_count) if max_count > 0 else 0
            bar = '█' * bar_length
            print(f"{guesses}: {bar} {count}")

    def get_possible_answers(self) -> Set[str]:
        """Return the current set of possible answers."""
        return self.possible_answers

def main():
    # Example usage
    optimizer = WordleOptimizer()
    
    print(f"{COLORS['bold']}Welcome to Wordle Optimizer!{COLORS['reset']}")
    print("Enter 'q' to quit, 's' to view statistics\n")
    
    while True:
        remaining = len(optimizer.get_possible_answers())
        print(f"\n{COLORS['bold']}Remaining possible answers:{COLORS['reset']} {remaining}")
        
        # Get best words for current guess
        best_words = optimizer.get_best_words()
        
        # For first two guesses, we use the predefined words
        if optimizer.current_guess_number <= len(BEST_STARTING_WORDS):
            word, desc = BEST_STARTING_WORDS[optimizer.current_guess_number - 1]
            print(f"\n{COLORS['bold']}Recommended word {optimizer.current_guess_number}:{COLORS['reset']}")
            print_suggestion(word, 0.0, desc)
        else:
            print(f"\n{COLORS['bold']}Top suggestions for next guess:{COLORS['reset']}")
            for word, score in best_words:
                print_suggestion(word, score)
        
        guess = input(f"\n{COLORS['bold']}Enter your guess:{COLORS['reset']} ").lower()
        if guess == 'q':
            break
        elif guess == 's':
            optimizer.print_statistics()
            continue
            
        pattern = input(f"{COLORS['bold']}Enter the pattern (2=green, 1=yellow, 0=gray):{COLORS['reset']} ")
        if not pattern.strip() or not all(c in '012' for c in pattern):
            print(f"{COLORS['yellow']}Invalid pattern! Use only 0, 1, and 2.{COLORS['reset']}")
            continue
            
        print(f"\nYou entered: {colorize_pattern(guess, pattern)}")
        optimizer.make_guess(guess, pattern)
        
        if len(optimizer.get_possible_answers()) <= 10:
            print(f"\n{COLORS['bold']}Possible answers:{COLORS['reset']}")
            for word in sorted(optimizer.get_possible_answers()):
                print(f"  {word.upper()}")
            
        if len(optimizer.get_possible_answers()) == 1:
            answer = next(iter(optimizer.get_possible_answers()))
            print(f"\n{COLORS['green']}{COLORS['bold']}Solved! The answer is: {answer.upper()}{COLORS['reset']}")
            optimizer.save_game(True)
            optimizer.print_statistics()
            break
        
        # Check for loss condition
        if optimizer.current_guess_number > optimizer.max_attempts:
            possible_answers = sorted(optimizer.get_possible_answers())
            print(f"\n{COLORS['yellow']}{COLORS['bold']}Game Over! Possible answers were:{COLORS['reset']}")
            for word in possible_answers:
                print(f"  {word.upper()}")
            optimizer.save_game(False)
            optimizer.print_statistics()
            break

if __name__ == "__main__":
    main() 