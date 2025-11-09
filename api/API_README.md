# Wordle Optimizer API

REST API for the Wordle optimization engine. This API provides endpoints to interact with the Wordle optimizer programmatically without interfering with existing command-line functionality.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the API

Start the API server:

```bash
python api.py
```

Or using uvicorn directly:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative docs**: `http://localhost:8000/redoc` (ReDoc)

## Endpoints

### `GET /`
Get API information and available endpoints.

### `POST /sessions`
Create a new Wordle game session.

**Response:**
```json
{
  "session_id": "uuid-string",
  "remaining_words": 2315,
  "current_guess_number": 1,
  "possible_answers": ["word1", "word2", ...]
}
```

### `GET /sessions/{session_id}`
Get the current state of a game session.

**Response:**
```json
{
  "session_id": "uuid-string",
  "remaining_words": 100,
  "current_guess_number": 2,
  "possible_answers": ["word1", "word2", ...],
  "game_history": {...},
  "guesses": ["salet"],
  "patterns": ["00000"]
}
```

### `POST /sessions/{session_id}/suggestions?n=5`
Get word suggestions for the next guess.

**Query Parameters:**
- `n`: Number of suggestions (1-20, default: 5)

**Response:**
```json
{
  "suggestions": [
    {"word": "salet", "score": 5.234},
    {"word": "crane", "score": 5.123}
  ],
  "remaining_words": 2315,
  "current_guess_number": 1
}
```

### `POST /sessions/{session_id}/guess`
Make a guess and update the game state with pattern feedback.

**Request Body:**
```json
{
  "guess": "salet",
  "pattern": "00000"
}
```

**Pattern Format:**
- `2` = Green (correct letter, correct position)
- `1` = Yellow (correct letter, wrong position)
- `0` = Gray (letter not in word)

**Response:**
```json
{
  "session_id": "uuid-string",
  "remaining_words": 100,
  "current_guess_number": 2,
  "possible_answers": ["word1", "word2", ...],
  "is_solved": false,
  "is_game_over": false
}
```

### `GET /sessions/{session_id}/statistics`
Get statistics for the current session.

**Response:**
```json
{
  "total_games": 5,
  "games_won": 4,
  "win_rate": 80.0,
  "average_guesses": 3.5,
  "guess_distribution": {
    "2": 1,
    "3": 2,
    "4": 1
  }
}
```

### `POST /sessions/{session_id}/reset`
Reset a game session to its initial state.

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "Session reset successfully"
}
```

### `DELETE /sessions/{session_id}`
Delete a game session.

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 3
}
```

## Example Usage

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a new session
response = requests.post(f"{BASE_URL}/sessions")
session = response.json()
session_id = session["session_id"]
print(f"Created session: {session_id}")

# Get suggestions
response = requests.post(f"{BASE_URL}/sessions/{session_id}/suggestions?n=5")
suggestions = response.json()
print(f"Top suggestions: {suggestions['suggestions']}")

# Make a guess
guess_data = {
    "guess": "salet",
    "pattern": "00000"  # All gray
}
response = requests.post(
    f"{BASE_URL}/sessions/{session_id}/guess",
    json=guess_data
)
result = response.json()
print(f"Remaining words: {result['remaining_words']}")

# Get updated suggestions
response = requests.post(f"{BASE_URL}/sessions/{session_id}/suggestions?n=5")
suggestions = response.json()
print(f"Next suggestions: {suggestions['suggestions']}")
```

### JavaScript/TypeScript Example

```javascript
const BASE_URL = 'http://localhost:8000';

// Create a new session
const sessionResponse = await fetch(`${BASE_URL}/sessions`, {
  method: 'POST'
});
const session = await sessionResponse.json();
const sessionId = session.session_id;

// Get suggestions
const suggestionsResponse = await fetch(
  `${BASE_URL}/sessions/${sessionId}/suggestions?n=5`,
  { method: 'POST' }
);
const suggestions = await suggestionsResponse.json();
console.log('Top suggestions:', suggestions.suggestions);

// Make a guess
const guessResponse = await fetch(
  `${BASE_URL}/sessions/${sessionId}/guess`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      guess: 'salet',
      pattern: '00000'
    })
  }
);
const result = await guessResponse.json();
console.log('Remaining words:', result.remaining_words);
```

### cURL Example

```bash
# Create session
SESSION_ID=$(curl -X POST http://localhost:8000/sessions | jq -r '.session_id')

# Get suggestions
curl -X POST "http://localhost:8000/sessions/$SESSION_ID/suggestions?n=5"

# Make a guess
curl -X POST "http://localhost:8000/sessions/$SESSION_ID/guess" \
  -H "Content-Type: application/json" \
  -d '{"guess": "salet", "pattern": "00000"}'

# Get statistics
curl "http://localhost:8000/sessions/$SESSION_ID/statistics"
```

## Integration with Next.js

For your Next.js portfolio, you can create API routes that proxy to this service, or call it directly from the client:

### Next.js API Route (Recommended)

```typescript
// app/api/wordle/solve/route.ts
import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.WORDLE_API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { sessionId, guess, pattern } = body;

  const response = await fetch(`${API_URL}/sessions/${sessionId}/guess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ guess, pattern }),
  });

  return NextResponse.json(await response.json());
}
```

### Direct Client Call

```typescript
// In your React component
const [sessionId, setSessionId] = useState<string | null>(null);

useEffect(() => {
  // Create session on mount
  fetch('http://localhost:8000/sessions', { method: 'POST' })
    .then(res => res.json())
    .then(data => setSessionId(data.session_id));
}, []);

const getSuggestions = async () => {
  if (!sessionId) return;
  const res = await fetch(
    `http://localhost:8000/sessions/${sessionId}/suggestions?n=5`,
    { method: 'POST' }
  );
  return res.json();
};
```

## CORS Configuration

The API is configured to allow CORS from all origins by default. For production, update the `allow_origins` in `api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Session Management

Sessions are stored in-memory by default. For production use, consider:
- Using Redis for session storage
- Adding session expiration
- Implementing authentication if needed

## Notes

- The API suppresses print statements from the optimizer to keep responses clean
- Sessions are stored in memory and will be lost on server restart
- The API doesn't interfere with existing command-line scripts (`automated_wordle.py`, `bots/wordle_optimizer.py`)
- Pattern format must be exactly 5 characters using only `0`, `1`, or `2`

