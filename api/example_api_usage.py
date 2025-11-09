"""
Example script demonstrating how to use the Wordle Optimizer API

This script shows how to interact with the API programmatically.
Run this after starting the API server with: python api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def create_session():
    """Create a new game session"""
    response = requests.post(f"{BASE_URL}/sessions")
    response.raise_for_status()
    session = response.json()
    print(f"✓ Created session: {session['session_id']}")
    print(f"  Remaining words: {session['remaining_words']}")
    return session['session_id']


def get_suggestions(session_id, n=5):
    """Get word suggestions"""
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/suggestions?n={n}")
    response.raise_for_status()
    data = response.json()
    print(f"\n✓ Top {len(data['suggestions'])} suggestions:")
    for i, suggestion in enumerate(data['suggestions'], 1):
        print(f"  {i}. {suggestion['word'].upper()} (score: {suggestion['score']:.3f} bits)")
    print(f"  Remaining words: {data['remaining_words']}")
    return data['suggestions']


def make_guess(session_id, guess, pattern):
    """Make a guess with pattern feedback"""
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/guess",
        json={"guess": guess, "pattern": pattern}
    )
    response.raise_for_status()
    result = response.json()
    print(f"\n✓ Made guess: {guess.upper()} with pattern {pattern}")
    print(f"  Remaining words: {result['remaining_words']}")
    print(f"  Current guess number: {result['current_guess_number']}")
    
    if result.get('is_solved'):
        print(f"  🎉 {result.get('message', 'Solved!')}")
    elif result.get('is_game_over'):
        print(f"  ⚠️  {result.get('message', 'Game over!')}")
    
    if result['remaining_words'] <= 10:
        print(f"  Possible answers: {', '.join([w.upper() for w in result['possible_answers'][:10]])}")
    
    return result


def get_statistics(session_id):
    """Get game statistics"""
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/statistics")
    response.raise_for_status()
    stats = response.json()
    print(f"\n✓ Statistics:")
    print(f"  Total games: {stats['total_games']}")
    print(f"  Games won: {stats['games_won']}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Average guesses: {stats['average_guesses']:.2f}")
    if stats['guess_distribution']:
        print(f"  Guess distribution: {stats['guess_distribution']}")
    return stats


def get_session_state(session_id):
    """Get current session state"""
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    response.raise_for_status()
    state = response.json()
    print(f"\n✓ Session state:")
    print(f"  Remaining words: {state['remaining_words']}")
    print(f"  Current guess number: {state['current_guess_number']}")
    print(f"  Guesses made: {', '.join([g.upper() for g in state['guesses']])}")
    print(f"  Patterns: {', '.join(state['patterns'])}")
    return state


def reset_session(session_id):
    """Reset the session"""
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/reset")
    response.raise_for_status()
    result = response.json()
    print(f"\n✓ {result['message']}")
    return result


def example_game():
    """Example: Play through a game"""
    print("=" * 60)
    print("Wordle Optimizer API Example")
    print("=" * 60)
    
    # Create session
    session_id = create_session()
    
    # Get initial suggestions
    suggestions = get_suggestions(session_id, n=5)
    
    # Make first guess (using top suggestion)
    first_guess = suggestions[0]['word']
    # Example pattern: all gray (word not in answer)
    make_guess(session_id, first_guess, "00000")
    
    # Get new suggestions
    suggestions = get_suggestions(session_id, n=5)
    
    # Make second guess
    second_guess = suggestions[0]['word']
    # Example pattern: one green, one yellow, rest gray
    make_guess(session_id, second_guess, "21000")
    
    # Get final suggestions
    suggestions = get_suggestions(session_id, n=5)
    
    # Get statistics
    get_statistics(session_id)
    
    # Get session state
    get_session_state(session_id)
    
    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # Check if API is running
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print("✓ API is running\n")
        
        # Run example
        example_game()
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API.")
        print("   Make sure the API server is running:")
        print("   python api.py")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

