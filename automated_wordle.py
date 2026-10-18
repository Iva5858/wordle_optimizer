import os
import time
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bots.wordle_optimizer import WordleOptimizer, colorize_pattern

class AutomatedWordle:
    def __init__(self):
        self.optimizer = WordleOptimizer()
        self.url = "https://www.nytimes.com/games/wordle/index.html"
        self.results_dir = "wordle_results"
        self.screenshots_dir = os.path.join(self.results_dir, "screenshots")
        
        # Create results directory if it doesn't exist
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            os.makedirs(self.screenshots_dir)

        # Initialize log file for this session
        self.log_file = os.path.join(self.results_dir, "wordle_log.txt")
        self.verbose_log = []  # Store verbose explanations during the game

    def log_to_file(self, message, prefix=""):
        """Log a message to the wordle log file."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {prefix}{message}\n")

    def explain_technical(self, message):
        """Log technical explanation."""
        self.log_to_file(message, "[TECHNICAL] ")
        self.verbose_log.append(("technical", message))

    def explain_simple(self, message):
        """Log simple explanation."""
        self.log_to_file(message, "[EXPLANATION] ")
        self.verbose_log.append(("simple", message))

    def log_guess_analysis(self, attempt, word, remaining_before, remaining_after, suggestions):
        """Log detailed analysis for each guess specific to this game."""
        self.log_to_file(f"\n--- GUESS #{attempt + 1}: {word.upper()} ---")
        
        # Log strategy explanation specific to this game state
        if attempt == 0:
            self.explain_technical(f"Starting with '{word.upper()}' - selected as the optimal opening word")
            self.explain_technical(f"This gives us information about 5 unique letters: {', '.join(word.upper())}")
            
            self.explain_simple(f"Beginning with '{word.upper()}' to test common letters")
            self.explain_simple(f"This word will reveal which of the letters {', '.join(word.upper())} are in today's answer")
            
        elif attempt == 1:
            # Get info about first guess results
            first_pattern = self.optimizer.current_game['patterns'][0] if self.optimizer.current_game['patterns'] else "00000"
            greens = first_pattern.count('2')
            yellows = first_pattern.count('1')
            grays = first_pattern.count('0')
            
            self.explain_technical(f"After first guess: {greens} correct positions, {yellows} correct letters in wrong positions, {grays} letters not in word")
            self.explain_technical(f"'{word.upper()}' chosen to explore new letters and narrow down {remaining_before} possibilities")
            
            self.explain_simple(f"First guess revealed {greens + yellows} letters from the answer")
            self.explain_simple(f"Trying '{word.upper()}' to test different letters and eliminate more possibilities")
            
        else:
            # Analyze what we've learned so far
            total_greens = sum(p.count('2') for p in self.optimizer.current_game['patterns'])
            total_yellows = sum(p.count('1') for p in self.optimizer.current_game['patterns'])
            
            self.explain_technical(f"Current knowledge: {total_greens} confirmed positions, {total_yellows} letters in wrong positions")
            self.explain_technical(f"'{word.upper()}' selected from {remaining_before} remaining possibilities")
            
            self.explain_simple(f"We've confirmed {total_greens} correct letter positions so far")
            self.explain_simple(f"Testing '{word.upper()}' - one of the {remaining_before} words that fit our clues")

        # Log word selection reasoning specific to this game
        if len(suggestions) > 1:
            alternatives = [s[0].upper() for s in suggestions[1:4]]
            self.log_to_file(f"Also considered: {', '.join(alternatives)}")
            if len(suggestions) > 1:
                score_diff = suggestions[0][1] - suggestions[1][1]
                self.explain_technical(f"'{word.upper()}' scored {score_diff:.3f} points higher than '{suggestions[1][0].upper()}'")
                self.explain_simple(f"'{word.upper()}' was the best choice among remaining candidates")

        self.log_to_file(f"Remaining possibilities before this guess: {remaining_before}")

    def setup_driver(self):
        """Initialize a headless Chrome WebDriver (Selenium Manager fetches the matching driver)."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        return webdriver.Chrome(options=options)

    def get_screenshot_path(self, filename):
        """Get the path for a screenshot, creating date directory if needed."""
        date_dir = os.path.join(self.screenshots_dir, datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        return os.path.join(date_dir, filename)

    def take_screenshot(self, driver, filename):
        """Take a screenshot of the game board."""
        try:
            game_board = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class^="Board-module_board"]'))
            )
            time.sleep(1)  # Wait for any animations
            screenshot_path = self.get_screenshot_path(filename)
            game_board.screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None

    def _visible(self, driver, by, selector):
        """Return the first visible element matching the selector, or None."""
        for el in driver.find_elements(by, selector):
            try:
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    def start_game(self, driver, timeout=60):
        """Click through whatever stands between page load and a playable board.

        The NYT flow varies by region and day (cookie banner, welcome screen,
        ad interstitial, help modal), so instead of waiting on each step in a
        fixed order we poll and dismiss whichever obstacle is currently showing.
        """
        # (description, locator) pairs, checked in order on every poll
        obstacles = [
            ("cookie banner", (By.XPATH, "//button[normalize-space()='Accept all' or normalize-space()='Accept All']")),
            ("terms prompt", (By.XPATH, "//button[normalize-space()='Continue']")),
            ("play button", (By.CSS_SELECTOR, 'button[data-testid="Play"]')),
            ("ad interstitial", (By.CSS_SELECTOR, 'button[class*="skipButton"]')),
            ("modal", (By.CSS_SELECTOR, '[data-testid="modal-overlay"] [data-testid="icon-close"], button[aria-label="Close"]')),
        ]
        board_selector = 'div[class^="Board-module_board"]'

        deadline = time.time() + timeout
        while time.time() < deadline:
            blocker = None
            for name, (by, selector) in obstacles:
                el = self._visible(driver, by, selector)
                if el:
                    blocker = name
                    print(f"Dismissing {name}...")
                    self.log_to_file(f"Dismissing {name}")
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(1)
                    break

            if not blocker and self._visible(driver, By.CSS_SELECTOR, board_selector):
                print("Game board ready")
                self.log_to_file("Game board ready")
                return True

            if not blocker:
                time.sleep(0.5)

        print("Timed out waiting for a playable game board")
        self.log_to_file("Timed out waiting for a playable game board")
        debug_screenshot = self.get_screenshot_path("debug_page.png")
        driver.save_screenshot(debug_screenshot)
        print(f"Saved debug screenshot to: {debug_screenshot}")
        return False

    def get_pattern_from_row(self, row):
        """Extract pattern from a completed row."""
        try:
            tiles = row.find_elements(By.CSS_SELECTOR, 'div[class^="Tile-module_tile"]')
            if not tiles or len(tiles) != 5:
                return None, None
            
            pattern = ''
            word = ''
            
            for tile in tiles:
                state = tile.get_attribute('data-state')
                letter = tile.text.lower()
                
                if not state or not letter:
                    return None, None
                
                if state == 'correct':
                    pattern += '2'
                elif state == 'present':
                    pattern += '1'
                elif state == 'absent':
                    pattern += '0'
                
                word += letter
            
            return word, pattern if len(pattern) == 5 else None
        except Exception as e:
            print(f"Error getting pattern from row: {e}")
            return None, None

    def play_wordle(self):
        """Play today's Wordle puzzle automatically."""
        print(f"\nStarting Wordle automation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_to_file(f"\n{'='*50}")
        self.log_to_file(f"WORDLE GAME - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_to_file(f"{'='*50}")
        
        driver = self.setup_driver()
        try:
            # Load the Wordle page and get to a playable board
            print("Loading Wordle page...")
            self.log_to_file("Loading Wordle page...")
            driver.get(self.url)
            if not self.start_game(driver):
                print("Failed to start the game")
                self.log_to_file("Failed to start the game")
                return
            
            # Initialize game state
            guesses = []
            patterns = []
            remaining_counts = []
            
            # Play the game
            for attempt in range(6):
                # Get remaining possibilities before guess
                remaining_before = len(self.optimizer.get_possible_answers())
                remaining_counts.append(remaining_before)
                
                # Get the best word to try
                suggestions = self.optimizer.get_best_words(3)
                if not suggestions:
                    print("No valid suggestions found!")
                    self.log_to_file("No valid suggestions found!")
                    break
                    
                word = suggestions[0][0].lower()
                print(f"\nTrying word: {word.upper()}")
                
                # Log analysis before making the guess
                self.log_guess_analysis(attempt, word, remaining_before, None, suggestions)
                
                # Type and submit the word
                actions = webdriver.ActionChains(driver)
                for letter in word:
                    actions.send_keys(letter)
                    time.sleep(0.1)
                actions.send_keys(Keys.RETURN)
                actions.perform()
                
                # Wait for animation to complete
                time.sleep(2)
                
                # Get the game rows
                rows = driver.find_elements(By.CSS_SELECTOR, 'div[class^="Row-module_row"]')
                if attempt >= len(rows):
                    print(f"Error: Could not find row {attempt + 1}")
                    self.log_to_file(f"Error: Could not find row {attempt + 1}")
                    break
                    
                current_row = rows[attempt]
                
                # Get the pattern from the current row
                word, pattern = self.get_pattern_from_row(current_row)
                if not pattern:
                    print("Failed to get pattern from row!")
                    self.log_to_file("Failed to get pattern from row!")
                    time.sleep(2)
                    word, pattern = self.get_pattern_from_row(current_row)
                    if not pattern:
                        break
                
                print(f"Result: {colorize_pattern(word, pattern)}")
                self.log_to_file(f"Pattern received: {pattern}")
                
                guesses.append(word)
                patterns.append(pattern)
                
                # Update the optimizer
                self.optimizer.make_guess(word, pattern)
                
                # Log analysis after getting the pattern
                remaining_after = len(self.optimizer.get_possible_answers())
                eliminated = remaining_before - remaining_after
                
                # Analyze pattern meaning for this specific guess
                greens = pattern.count('2')
                yellows = pattern.count('1') 
                grays = pattern.count('0')
                
                self.explain_technical(f"Pattern result: {greens} green (correct position), {yellows} yellow (wrong position), {grays} gray (not in word)")
                self.explain_technical(f"This feedback eliminated {eliminated} possibilities ({eliminated/remaining_before*100:.1f}%)")
                self.explain_technical(f"Narrowed down to {remaining_after} possible answers")
                
                # Describe what the colors mean for this specific word
                color_feedback = []
                for i, (letter, code) in enumerate(zip(word, pattern)):
                    if code == '2':
                        color_feedback.append(f"{letter.upper()} is correct in position {i+1}")
                    elif code == '1':
                        color_feedback.append(f"{letter.upper()} is in the word but not in position {i+1}")
                    else:
                        color_feedback.append(f"{letter.upper()} is not in today's word")
                
                self.explain_simple("Feedback breakdown:")
                for feedback in color_feedback:
                    self.explain_simple(f"  • {feedback}")
                
                if remaining_after <= 10 and remaining_after > 1:
                    remaining_words = sorted(list(self.optimizer.get_possible_answers()))
                    self.log_to_file(f"Remaining possible answers: {', '.join(w.upper() for w in remaining_words)}")
                    self.explain_simple(f"Possible words left: {', '.join(w.upper() for w in remaining_words)}")
                elif remaining_after == 1:
                    final_word = next(iter(self.optimizer.get_possible_answers()))
                    self.explain_simple(f"Only one word matches all clues: {final_word.upper()}")
                
                # Check if we won
                if pattern == '22222':
                    print(f"\nSolved in {attempt + 1} attempts!")
                    self.log_to_file(f"SOLVED in {attempt + 1} attempts!")
                    self.explain_technical(f"Success! Found the answer in {attempt + 1} guesses")
                    self.explain_simple(f"Puzzle solved! The word was '{word.upper()}'")
                    break
                
                # Take a screenshot after each guess
                self.take_screenshot(driver, f"guess_{attempt + 1}.png")
            
            # Take final screenshot
            final_screenshot = self.take_screenshot(driver, "final.png")
            
            # Save results to log file
            self.log_results(guesses, patterns, final_screenshot, remaining_counts)
            
        except Exception as e:
            print(f"Error during gameplay: {e}")
            self.log_to_file(f"Error during gameplay: {e}")
            import traceback
            traceback.print_exc()
        finally:
            driver.quit()

    def log_results(self, guesses, patterns, final_screenshot, remaining_counts):
        """Log the results of the game with analysis specific to this day's puzzle."""
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"GAME SUMMARY - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"Completed: {date_str}\n")
            f.write(f"Number of guesses: {len(guesses)}\n")
            f.write(f"Result: {'WON' if patterns and patterns[-1] == '22222' else 'LOST'}\n")
            f.write(f"Final screenshot: {final_screenshot}\n\n")
            
            f.write("Game progression:\n")
            for i, (word, pattern) in enumerate(zip(guesses, patterns)):
                remaining = remaining_counts[i] if i < len(remaining_counts) else 'N/A'
                # Add pattern interpretation
                greens = pattern.count('2')
                yellows = pattern.count('1')
                f.write(f"Guess {i+1}: {word.upper()} → {pattern} ({greens}G, {yellows}Y) → {remaining} words left\n")
            
            # Generate summary paragraph specific to this game
            f.write(f"\nGAME ANALYSIS:\n")
            
            if guesses:
                won = patterns and patterns[-1] == '22222'
                num_guesses = len(guesses)
                final_word = guesses[-1].upper() if guesses else "UNKNOWN"
                
                # Get final remaining count early
                final_remaining = len(self.optimizer.get_possible_answers()) if self.optimizer.get_possible_answers() else 0
                
                # Analyze the game's progression
                summary = f"Today's Wordle"
                if won:
                    summary += f" was solved in {num_guesses} guess{'es' if num_guesses != 1 else ''}. "
                    summary += f"The answer was '{final_word}'. "
                else:
                    summary += f" remained unsolved after {num_guesses} attempts. "
                
                # Describe how the game unfolded
                if len(guesses) >= 1:
                    first_pattern = patterns[0]
                    first_greens = first_pattern.count('2')
                    first_yellows = first_pattern.count('1')
                    if first_greens > 0:
                        summary += f"The opening word '{guesses[0].upper()}' immediately revealed {first_greens} correct position{'s' if first_greens != 1 else ''}"
                        if first_yellows > 0:
                            summary += f" and {first_yellows} letter{'s' if first_yellows != 1 else ''} in wrong positions. "
                        else:
                            summary += ". "
                    elif first_yellows > 0:
                        summary += f"'{guesses[0].upper()}' found {first_yellows} correct letter{'s' if first_yellows != 1 else ''} but in wrong positions. "
                    else:
                        summary += f"'{guesses[0].upper()}' contained none of today's letters. "
                
                # Describe key turning points
                if len(guesses) >= 2:
                    second_pattern = patterns[1]
                    total_info_after_two = sum(p.count('2') + p.count('1') for p in patterns[:2])
                    remaining_after_two = remaining_counts[1] if len(remaining_counts) > 1 else 0
                    summary += f"After two guesses, {total_info_after_two} letters were identified, narrowing to {remaining_after_two} possibilities. "
                
                # Describe final resolution
                if won:
                    if num_guesses <= 3:
                        summary += f"The puzzle was solved quickly, with '{final_word}' identified efficiently. "
                    elif num_guesses <= 4:
                        summary += f"'{final_word}' was found after a systematic elimination process. "
                    else:
                        summary += f"'{final_word}' required careful deduction through multiple attempts. "
                    
                    # Check if the final guess was obvious
                    if len(remaining_counts) >= num_guesses and remaining_counts[num_guesses-1] == 1:
                        summary += "The final guess was the only remaining possibility. "
                    else:
                        summary += f"'{final_word}' was selected from the remaining candidates. "
                else:
                    if final_remaining > 0:
                        remaining_words = sorted(list(self.optimizer.get_possible_answers()))[:3]
                        summary += f"The word was likely one of: {', '.join(w.upper() for w in remaining_words)}. "
                    
                # Analyze efficiency
                if remaining_counts:
                    start_words = remaining_counts[0]
                    elimination_efficiency = ((start_words - final_remaining) / start_words * 100) if start_words > 0 else 0
                    summary += f"The strategy eliminated {elimination_efficiency:.1f}% of possible words, "
                    
                    # Find the most effective guess
                    if len(remaining_counts) > 1:
                        biggest_drop = 0
                        best_guess_num = 1
                        for i in range(1, len(remaining_counts)):
                            drop = remaining_counts[i-1] - remaining_counts[i]
                            if drop > biggest_drop:
                                biggest_drop = drop
                                best_guess_num = i + 1
                        summary += f"with guess #{best_guess_num} ('{guesses[best_guess_num-1].upper()}') being most effective, eliminating {biggest_drop} possibilities."
                    else:
                        summary += "demonstrating systematic word elimination."
                
                f.write(summary + "\n")
            
            f.write(f"{'='*50}\n")

def run_daily_wordle():
    """Function to be scheduled for daily execution."""
    bot = AutomatedWordle()
    bot.play_wordle()

def main():
    print("Starting Automated Wordle Bot")
    print("Scheduling daily runs at 0:00 AM")
    
    # Schedule the job to run daily at 6:00 AM
    schedule.every().day.at("00:00").do(run_daily_wordle)
    
    # Run immediately if requested
    if input("Would you like to run now? (y/n): ").lower() == 'y':
        run_daily_wordle()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 