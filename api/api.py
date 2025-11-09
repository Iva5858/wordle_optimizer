"""
FastAPI server for Wordle Optimizer

This API provides REST endpoints to interact with the Wordle optimizer
without interfering with existing command-line functionality.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
import uuid
from bots.wordle_optimizer import WordleOptimizer

app = FastAPI(
    title="Wordle Optimizer API",
    description="API for the Wordle optimization engine using entropy calculations",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (in production, use Redis or a database)
sessions: Dict[str, WordleOptimizer] = {}


# Request/Response Models
class GuessRequest(BaseModel):
    guess: str = Field(..., min_length=5, max_length=5, description="5-letter word guess")
    pattern: str = Field(..., min_length=5, max_length=5, description="Pattern: 2=green, 1=yellow, 0=gray")


class SessionResponse(BaseModel):
    session_id: str
    remaining_words: int
    current_guess_number: int
    possible_answers: List[str] = Field(default_factory=list)


class SuggestionsResponse(BaseModel):
    suggestions: List[Dict[str, float]]
    remaining_words: int
    current_guess_number: int


class GameStateResponse(BaseModel):
    session_id: str
    remaining_words: int
    current_guess_number: int
    possible_answers: List[str]
    game_history: Dict
    guesses: List[str]
    patterns: List[str]


class StatisticsResponse(BaseModel):
    total_games: int
    games_won: int
    win_rate: float
    average_guesses: float
    guess_distribution: Dict[int, int]


class ResetResponse(BaseModel):
    session_id: str
    message: str


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Wordle Optimizer API",
        "version": "1.0.0",
        "endpoints": {
            "POST /sessions": "Create a new game session",
            "GET /sessions/{session_id}": "Get current game state",
            "POST /sessions/{session_id}/suggestions": "Get word suggestions",
            "POST /sessions/{session_id}/guess": "Make a guess with pattern feedback",
            "GET /sessions/{session_id}/statistics": "Get game statistics",
            "POST /sessions/{session_id}/reset": "Reset the game session",
            "DELETE /sessions/{session_id}": "Delete a session"
        }
    }


@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    """
    Create a new Wordle game session.
    
    Returns a session_id that should be used for subsequent requests.
    """
    session_id = str(uuid.uuid4())
    # Use relative paths from project root
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    word_list_file = os.path.join(base_dir, "words", "words.txt")
    answers_file = os.path.join(base_dir, "words", "answers.txt")
    optimizer = WordleOptimizer(word_list_file=word_list_file, answers_file=answers_file)
    sessions[session_id] = optimizer
    
    remaining = len(optimizer.get_possible_answers())
    
    return SessionResponse(
        session_id=session_id,
        remaining_words=remaining,
        current_guess_number=optimizer.current_guess_number,
        possible_answers=sorted(list(optimizer.get_possible_answers()))[:50]  # Limit to 50 for response size
    )


@app.get("/sessions/{session_id}", response_model=GameStateResponse)
async def get_session_state(session_id: str):
    """
    Get the current state of a game session.
    
    Returns remaining words, current guess number, and game history.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    optimizer = sessions[session_id]
    remaining = len(optimizer.get_possible_answers())
    possible_answers = sorted(list(optimizer.get_possible_answers()))
    
    return GameStateResponse(
        session_id=session_id,
        remaining_words=remaining,
        current_guess_number=optimizer.current_guess_number,
        possible_answers=possible_answers[:100],  # Limit to 100 for response size
        game_history=optimizer.current_game,
        guesses=optimizer.current_game.get('guesses', []),
        patterns=optimizer.current_game.get('patterns', [])
    )


@app.post("/sessions/{session_id}/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(session_id: str, n: int = 5):
    """
    Get word suggestions for the next guess.
    
    Args:
        session_id: The session ID
        n: Number of suggestions to return (default: 5, max: 20)
    
    Returns top n word suggestions with their scores.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if n < 1 or n > 20:
        raise HTTPException(status_code=400, detail="n must be between 1 and 20")
    
    optimizer = sessions[session_id]
    
    # Suppress print statements by redirecting stdout temporarily
    import sys
    from io import StringIO
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        best_words = optimizer.get_best_words(n=n)
    finally:
        sys.stdout = old_stdout
    
    suggestions = [{"word": word, "score": float(score)} for word, score in best_words]
    remaining = len(optimizer.get_possible_answers())
    
    return SuggestionsResponse(
        suggestions=suggestions,
        remaining_words=remaining,
        current_guess_number=optimizer.current_guess_number
    )


@app.post("/sessions/{session_id}/guess")
async def make_guess(session_id: str, request: GuessRequest):
    """
    Make a guess and update the game state with pattern feedback.
    
    Args:
        session_id: The session ID
        request: Contains guess (5-letter word) and pattern (5-character string: 2=green, 1=yellow, 0=gray)
    
    Pattern format:
    - '2' = Green (correct letter, correct position)
    - '1' = Yellow (correct letter, wrong position)
    - '0' = Gray (letter not in word)
    
    Example: "22001" means first two letters are green, third is yellow, last two are gray.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    guess = request.guess.lower().strip()
    pattern = request.pattern.strip()
    
    # Validate guess
    if len(guess) != 5 or not guess.isalpha():
        raise HTTPException(status_code=400, detail="Guess must be exactly 5 letters")
    
    # Validate pattern
    if len(pattern) != 5 or not all(c in '012' for c in pattern):
        raise HTTPException(status_code=400, detail="Pattern must be exactly 5 characters using only 0, 1, or 2")
    
    optimizer = sessions[session_id]
    
    # Check if guess is valid
    if guess not in optimizer.all_words:
        raise HTTPException(status_code=400, detail=f"'{guess}' is not a valid Wordle word")
    
    # Suppress print statements
    import sys
    from io import StringIO
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        optimizer.make_guess(guess, pattern)
    finally:
        sys.stdout = old_stdout
    
    remaining = len(optimizer.get_possible_answers())
    possible_answers = sorted(list(optimizer.get_possible_answers()))
    
    # Check win condition
    is_solved = remaining == 1
    is_game_over = optimizer.current_guess_number > optimizer.max_attempts
    
    response_data = {
        "session_id": session_id,
        "remaining_words": remaining,
        "current_guess_number": optimizer.current_guess_number,
        "possible_answers": possible_answers[:100],  # Limit to 100
        "is_solved": is_solved,
        "is_game_over": is_game_over
    }
    
    if is_solved:
        answer = possible_answers[0] if possible_answers else None
        optimizer.save_game(True)
        response_data["answer"] = answer
        response_data["message"] = f"Solved! The answer is {answer.upper()}"
    elif is_game_over:
        optimizer.save_game(False)
        response_data["message"] = "Game over! Maximum attempts reached."
    
    return response_data


@app.get("/sessions/{session_id}/statistics", response_model=StatisticsResponse)
async def get_statistics(session_id: str):
    """
    Get statistics for the current session.
    
    Returns win rate, average guesses, and guess distribution.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    optimizer = sessions[session_id]
    stats = optimizer.get_statistics()
    
    if not stats:
        return StatisticsResponse(
            total_games=0,
            games_won=0,
            win_rate=0.0,
            average_guesses=0.0,
            guess_distribution={}
        )
    
    return StatisticsResponse(**stats)


@app.post("/sessions/{session_id}/reset", response_model=ResetResponse)
async def reset_session(session_id: str):
    """
    Reset a game session to its initial state.
    
    This clears the current game but preserves statistics.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    optimizer = sessions[session_id]
    
    # Reset game state
    optimizer.current_guess_number = 1
    optimizer.current_game = {
        'guesses': [],
        'patterns': [],
        'remaining_words': []
    }
    
    # Reload possible answers
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    answers_file = os.path.join(base_dir, "words", "answers.txt")
    try:
        with open(answers_file, 'r') as f:
            optimizer.possible_answers = {word.strip().lower() for word in f.readlines()}
    except FileNotFoundError:
        optimizer.possible_answers = optimizer.all_words.copy()
    
    return ResetResponse(
        session_id=session_id,
        message="Session reset successfully"
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a game session.
    
    This removes the session from memory.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    return {"message": "Session deleted successfully"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "active_sessions": len(sessions)}


if __name__ == "__main__":
    import uvicorn
    import os
    # Use PORT environment variable for Render, default to 8000 for local
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

