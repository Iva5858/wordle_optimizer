import os
import time
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
        """Initialize the Chrome WebDriver with necessary options."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        
        # Add additional options to avoid detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        # Initialize Chrome with the latest driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute CDP commands to avoid detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        
        # Execute JavaScript to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

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

    def wait_for_board(self, driver):
        """Wait for the game board to be fully loaded and visible."""
        try:
            # First wait for the page to be interactive
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Try multiple selectors for the game board
            board_selectors = [
                'div[class^="Board-module_board"]',
                'div[class*="board"]',
                'div[data-testid="board"]',
                '#board',
                'div.Board-module_board__'
            ]
            
            for selector in board_selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found game board with selector: {selector}")
                    time.sleep(2)  # Additional wait for animations
                    return True
                except TimeoutException:
                    continue
            
            # If we get here, we couldn't find the board with any selector
            print("Could not find game board with any known selector")
            
            # Take a full page screenshot for debugging
            debug_screenshot = self.get_screenshot_path("debug_page.png")
            driver.save_screenshot(debug_screenshot)
            print(f"Saved debug screenshot to: {debug_screenshot}")
            
            # Print page source for debugging
            print("\nPage source:")
            print(driver.page_source[:500] + "...")  # Print first 500 chars
            
            return False
            
        except TimeoutException:
            print("Timeout waiting for game board to load")
            return False
        except Exception as e:
            print(f"Error while waiting for board: {e}")
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

    def close_modals(self, driver):
        """Close any modals that might appear (instructions, statistics, etc.)."""
        try:
            # Wait for any modal to appear
            modal_selectors = [
                'div[class^="Modal-module"]',
                'div[data-testid="modal"]',
                'div.Modal-module_modal',
                '#modal'
            ]
            
            for selector in modal_selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    time.sleep(1)
                    
                    # Try to find and click the close button
                    close_selectors = [
                        'button[class^="Modal-module_closeIcon"]',
                        'button[aria-label="Close"]',
                        'button.Modal-module_closeIcon__TcEKb',
                        'button[class*="close"]',
                        'button[data-testid="close-button"]'
                    ]
                    
                    for close_selector in close_selectors:
                        try:
                            close_button = driver.find_element(By.CSS_SELECTOR, close_selector)
                            driver.execute_script("arguments[0].click();", close_button)
                            time.sleep(1)
                            return
                        except:
                            continue
                            
                    # If we can't find a close button, try pressing Escape
                    actions = webdriver.ActionChains(driver)
                    actions.send_keys(Keys.ESCAPE)
                    actions.perform()
                    time.sleep(1)
                    
                except TimeoutException:
                    continue
                    
        except Exception as e:
            print(f"Error closing modals: {e}")
            pass

    def verify_button_click(self, driver, button_type):
        """Verify if a button was successfully clicked by checking for its disappearance."""
        try:
            time.sleep(2)  # Wait for any animations
            if button_type == "cookie":
                # Try to find the cookie banner or accept button
                elements = driver.find_elements(By.CSS_SELECTOR, 
                    'button[class*="accept"], div[class*="cookie"], div[class*="Cookie"]'
                )
                # If we can't find any cookie-related elements, consider it successful
                return len(elements) == 0
            elif button_type == "terms":
                # Try to find the terms modal or continue button
                elements = driver.find_elements(By.CSS_SELECTOR, 
                    'button:contains("Continue"), div[class*="terms"], div[class*="Terms"]'
                )
                # If we can't find any terms-related elements, consider it successful
                return len(elements) == 0
            return True  # Default to success if button_type is unknown
        except:
            return True  # If we can't verify, assume success

    def accept_cookies_and_terms(self, driver):
        """Handle cookie consent and terms acceptance."""
        try:
            success = True  # Track overall success
            
            # Wait for and accept cookies
            print("Looking for cookie consent button...")
            cookie_selectors = [
                'button.css-1qj7uk2',  # Accept all button
                'button[data-testid="accept-all-cookies"]',
                'button.accept-all',
                'button[data-testid="cookie-accept"]',
                'button.cookie-accept',
                'button[class*="accept"]',
                'button:contains("Accept all")'
            ]
            
            cookie_clicked = False
            for selector in cookie_selectors:
                try:
                    cookie_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found cookie button with selector: {selector}")
                    driver.execute_script("arguments[0].click();", cookie_button)
                    cookie_clicked = True
                    print("Successfully accepted cookies")
                    time.sleep(2)  # Wait for any animations
                    break
                except:
                    continue

            # If CSS selectors fail, try finding by text
            if not cookie_clicked:
                try:
                    cookie_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept all')]")
                    driver.execute_script("arguments[0].click();", cookie_button)
                    cookie_clicked = True
                    print("Successfully accepted cookies (found by text)")
                    time.sleep(2)
                except:
                    print("Could not find cookie button")
                    success = False

            # Wait for and accept terms
            print("Looking for terms acceptance button...")
            terms_selectors = [
                'button.css-1qj7uk2',  # Continue button
                'button[data-testid="terms-continue"]',
                'button.continue-button',
                'button[class*="continue"]',
                'button.Continue',
                'button:contains("Continue")'
            ]
            
            terms_clicked = False
            for selector in terms_selectors:
                try:
                    terms_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found terms button with selector: {selector}")
                    driver.execute_script("arguments[0].click();", terms_button)
                    terms_clicked = True
                    print("Successfully accepted terms")
                    time.sleep(2)
                    break
                except:
                    continue

            # If CSS selectors fail, try finding by text
            if not terms_clicked:
                try:
                    terms_button = driver.find_element(By.XPATH, "//button[text()='Continue']")
                    driver.execute_script("arguments[0].click();", terms_button)
                    terms_clicked = True
                    print("Successfully accepted terms (found by text)")
                    time.sleep(2)
                except:
                    print("Could not find terms button")
                    success = False


            # Return true if either both buttons were clicked or if we couldn't find them
            # (which might mean they weren't needed)
            return success and (cookie_clicked or not self.verify_button_click(driver, "cookie")) and \
                   (terms_clicked or not self.verify_button_click(driver, "terms"))

        except Exception as e:
            print(f"Error handling cookies and terms: {e}")
            # Save debug screenshot
            try:
                driver.save_screenshot(self.get_screenshot_path("error_cookies_terms.png"))
            except:
                pass
            return False

    def click_play_button(self, driver):
        """Find and click the play button."""
        try:
            print("Looking for play button...")
            play_selectors = [
                'Welcome-module_button__ZG0Zh'
                'button.css-1qj7uk2',  # The play button class
                'button.play-button',
                'button[class*="play"]',
                'button[class*="Play"]',
                'button:contains("Play")',
                'a[class*="play"]',
                'button.css-1qj7uk2[data-testid="Play"]'  # Most specific selector
            ]
            
            for selector in play_selectors:
                try:
                    play_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    driver.execute_script("arguments[0].click();", play_button)
                    print("Clicked play button")
                    time.sleep(2)  # Wait for game to load
                    return True
                except:
                    continue
            
            # If we couldn't find the button by class, try finding by text content
            try:
                play_button = driver.find_element(By.XPATH, "//button[text()='Play']")
                driver.execute_script("arguments[0].click();", play_button)
                print("Clicked play button (found by text)")
                time.sleep(2)
                return True
            except:
                pass
            
            print("Could not find play button")
            return False

        except Exception as e:
            print(f"Error clicking play button: {e}")
            return False

    def play_wordle(self):
        """Play today's Wordle puzzle automatically."""
        print(f"\nStarting Wordle automation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_to_file(f"\n{'='*50}")
        self.log_to_file(f"WORDLE GAME - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_to_file(f"{'='*50}")
        
        driver = self.setup_driver()
        try:
            # Load the Wordle page
            print("Loading Wordle page...")
            self.log_to_file("Loading Wordle page...")
            driver.get(self.url)
            
            # Wait for page to be ready
            print("Waiting for page to be ready...")
            self.log_to_file("Waiting for page to be ready...")
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(3)
            
            # Handle cookies and terms
            print("Handling cookies and terms...")
            self.log_to_file("Handling cookies and terms...")
            if not self.accept_cookies_and_terms(driver):
                print("Failed to accept cookies and terms")
                self.log_to_file("Failed to accept cookies and terms")
                driver.save_screenshot(self.get_screenshot_path("failed_cookies_terms.png"))
                print("Refreshing page and trying again...")
                driver.refresh()
                time.sleep(3)
                if not self.accept_cookies_and_terms(driver):
                    print("Failed to accept cookies and terms after retry")
                    self.log_to_file("Failed to accept cookies and terms after retry")
                    pass
            
            # Click play button
            print("Looking for play button...")
            self.log_to_file("Looking for play button...")
            if not self.click_play_button(driver):
                print("Failed to start the game")
                self.log_to_file("Failed to start the game")
                return
            
            # Wait for the game board to load
            print("Waiting for game board...")
            self.log_to_file("Waiting for game board...")
            if not self.wait_for_board(driver):
                print("Failed to load game board")
                self.log_to_file("Failed to load game board")
                return
            
            print("Game board loaded successfully")
            self.log_to_file("Game board loaded successfully")
            
            # Close any modals
            print("Closing modals...")
            self.log_to_file("Closing modals...")
            self.close_modals(driver)
            
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