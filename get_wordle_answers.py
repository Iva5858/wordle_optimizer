import requests
from datetime import datetime, timedelta
import json

def get_wordle_answers():
    # Start date of Wordle (October 1, 2021)
    start_date = datetime(2021, 10, 1)
    end_date = datetime.now()
    
    # List to store all answers
    answers = []
    
    # Base URL for the API
    base_url = "https://www.nytimes.com/svc/wordle/v2/{}.json"
    
    # Iterate through each date
    current_date = start_date
    while current_date <= end_date:
        # Format the date for the URL
        formatted_date = current_date.strftime("%Y-%m-%d")
        url = base_url.format(formatted_date)
        
        try:
            # Make the API request
            response = requests.get(url)
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                answers.append(data["solution"].lower())
                print(f"Successfully fetched answer for {formatted_date}: {data['solution']}")
            else:
                print(f"Failed to fetch data for {formatted_date}: Status code {response.status_code}")
        
        except Exception as e:
            print(f"Error fetching data for {formatted_date}: {str(e)}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    return answers

def save_answers_to_file(answers, filename="words/past_answers.txt"):
    # Save answers to file, one per line
    with open(filename, 'w') as f:
        for answer in answers:
            f.write(answer + '\n')
    print(f"\nSaved {len(answers)} answers to {filename}")

if __name__ == "__main__":
    print("Fetching Wordle answers from NYT API...")
    answers = get_wordle_answers()
    save_answers_to_file(answers) 