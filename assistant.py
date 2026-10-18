"""Get the bot's suggestions while you play Wordle yourself.

    python assistant.py

After each guess, type the colors you got: 2 = green, 1 = yellow, 0 = gray.
"""
from wordle.feedback import ALL_GREEN
from wordle.player import Player

COLORS = {"2": "\033[42;30m", "1": "\033[43;30m", "0": "\033[100;97m"}


def colored(word: str, pattern: str) -> str:
    return "".join(f"{COLORS[p]} {c.upper()} \033[0m" for c, p in zip(word, pattern))


def ask(prompt: str, valid) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if valid(answer):
            return answer
        print("  Try again.")


def main():
    player = Player.from_files()
    allowed = set(player.guesses)

    for turn in range(1, 7):
        suggestion = player.next_guess()
        print(f"\nGuess {turn}: try {suggestion.upper()}")
        guess = ask(f"  Word you played [{suggestion.upper()}]: ", lambda w: not w or w in allowed) or suggestion
        pattern = ask("  Colors (e.g. 20110): ", lambda p: len(p) == 5 and set(p) <= set("012"))
        try:
            player.record(guess, pattern)
        except ValueError as error:
            print(f"  {error}. Check the colors and try again.")
            continue
        print(f"  {colored(guess, pattern)}")

        if pattern == ALL_GREEN:
            print(f"\nSolved in {turn}!")
            return
        left = player.candidates
        print(f"  {len(left)} possible answer{'s' if len(left) != 1 else ''} left"
              + (f": {', '.join(w.upper() for w in left)}" if len(left) <= 10 else ""))

    print("\nOut of guesses.")


if __name__ == "__main__":
    main()
