"""Play today's NYT Wordle in Chrome.

    python automated_wordle.py                 # play once now
    python automated_wordle.py --daily 00:05   # keep running, play every day at 00:05
    python automated_wordle.py --show          # show the browser window instead of headless

Screenshots go to wordle_results/screenshots/<date>/ and a summary of each
game is appended to wordle_results/wordle_log.txt.
"""
import argparse
import time
from datetime import datetime

import schedule
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from wordle.data import RESULTS_DIR
from wordle.player import Player

URL = "https://www.nytimes.com/games/wordle/index.html"
BOARD = 'div[class^="Board-module_board"]'
ROW = 'div[class^="Row-module_row"]'
TILE = 'div[class^="Tile-module_tile"]'
TILE_COLORS = {"correct": "2", "present": "1", "absent": "0"}

# What can stand between page load and the board, dismissed in whatever order it shows up
OBSTACLES = [
    ("cookie banner", By.XPATH, "//button[normalize-space()='Accept all' or normalize-space()='Accept All']"),
    ("terms prompt", By.XPATH, "//button[normalize-space()='Continue']"),
    ("welcome screen", By.CSS_SELECTOR, 'button[data-testid="Play"]'),
    ("ad", By.CSS_SELECTOR, 'button[class*="skipButton"]'),
    ("popup", By.CSS_SELECTOR, '[data-testid="modal-overlay"] [data-testid="icon-close"], button[aria-label="Close"]'),
]


def make_driver(headless: bool = True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=options)


def first_visible(driver, by, selector):
    for element in driver.find_elements(by, selector):
        try:
            if element.is_displayed():
                return element
        except Exception:  # the element disappeared while we looked at it
            continue
    return None


def open_game(driver, timeout: float = 60) -> bool:
    """Load Wordle and click through until the board is playable."""
    driver.get(URL)
    deadline = time.time() + timeout
    while time.time() < deadline:
        for name, by, selector in OBSTACLES:
            button = first_visible(driver, by, selector)
            if button:
                print(f"Dismissing {name}")
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
                break
        else:
            if first_visible(driver, By.CSS_SELECTOR, BOARD):
                return True
            time.sleep(0.5)
    return False


def submit(driver, word: str, row: int, timeout: float = 10):
    """Type a guess and return its colors, or None if the row never revealed (word rejected)."""
    webdriver.ActionChains(driver).send_keys(word).send_keys(Keys.ENTER).perform()

    def revealed(driver):
        tiles = driver.find_elements(By.CSS_SELECTOR, ROW)[row].find_elements(By.CSS_SELECTOR, TILE)
        states = [tile.get_attribute("data-state") for tile in tiles]
        settled = all(tile.get_attribute("data-animation") == "idle" for tile in tiles)
        if settled and all(state in TILE_COLORS for state in states):
            return "".join(TILE_COLORS[state] for state in states)
        return False

    try:
        return WebDriverWait(driver, timeout, poll_frequency=0.2).until(revealed)
    except TimeoutException:
        return None


def screenshot(driver, name: str):
    """Save the board (or the whole page if there's no board) to today's screenshot folder."""
    folder = RESULTS_DIR / "screenshots" / datetime.now().strftime("%Y%m%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    board = first_visible(driver, By.CSS_SELECTOR, BOARD)
    if board:
        board.screenshot(str(path))
    else:
        driver.save_screenshot(str(path))
    return path


def play_today(headless: bool = True):
    print(f"Playing Wordle, {datetime.now():%Y-%m-%d %H:%M}")
    player = Player.from_files()
    driver = make_driver(headless)
    lines = []

    def report(line):
        print(line)
        lines.append(line)

    try:
        if not open_game(driver):
            report(f"Couldn't reach the game board, see {screenshot(driver, 'debug_page.png')}")
            return

        for turn in range(1, 7):
            before = len(player.candidates)
            guess = player.next_guess()
            pattern = submit(driver, guess, turn - 1)
            if pattern is None:
                report(f"{guess.upper()} was not accepted")
                break
            player.record(guess, pattern)
            screenshot(driver, f"guess_{turn}.png")
            report(f"{turn}. {guess.upper()}  {pattern}  {before} -> {len(player.candidates)} possible")
            if player.solved:
                break

        report(f"Solved in {len(player.history)}" if player.solved else "Not solved")
    finally:
        driver.quit()
        RESULTS_DIR.mkdir(exist_ok=True)
        with open(RESULTS_DIR / "wordle_log.txt", "a", encoding="utf-8") as log:
            log.write(f"\n{datetime.now():%Y-%m-%d %H:%M}\n" + "".join(f"  {line}\n" for line in lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--daily", metavar="HH:MM", help="keep running and play every day at this time")
    parser.add_argument("--show", action="store_true", help="show the browser window")
    args = parser.parse_args()

    if not args.daily:
        play_today(headless=not args.show)
        return

    schedule.every().day.at(args.daily).do(play_today, headless=not args.show)
    print(f"Playing every day at {args.daily}. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
