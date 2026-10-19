"""Download every NYT Wordle answer so far into words/past_answers.txt.

    python fetch_past_answers.py

Used by benchmark.py to measure the bot on real games.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.request import Request, urlopen

from wordle.data import PAST_ANSWERS_FILE

FIRST_WORDLE = date(2021, 6, 19)
ANSWER_URL = "https://www.nytimes.com/svc/wordle/v2/{}.json"


def answer_for(day: date):
    request = Request(ANSWER_URL.format(day.isoformat()), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)["solution"].lower()
    except Exception as error:
        print(f"{day}: {error}")
        return None


def main():
    days = [FIRST_WORDLE + timedelta(n) for n in range((date.today() - FIRST_WORDLE).days + 1)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        answers = [a for a in pool.map(answer_for, days) if a]
    PAST_ANSWERS_FILE.write_text("".join(f"{a}\n" for a in answers))
    shown = PAST_ANSWERS_FILE.relative_to(PAST_ANSWERS_FILE.parent.parent)
    print(f"Saved {len(answers)} answers to {shown}")


if __name__ == "__main__":
    main()
