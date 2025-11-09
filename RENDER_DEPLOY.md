# Deploying Wordle Optimizer API to Render

This guide will help you deploy the Wordle Optimizer API to Render.

## Prerequisites

1. A [Render](https://render.com) account (free tier works)
2. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### Option 1: Using Render Dashboard (Recommended)

1. **Log in to Render**
   - Go to [dashboard.render.com](https://dashboard.render.com)
   - Sign up or log in

2. **Create a New Web Service**
   - Click "New +" → "Web Service"
   - Connect your Git repository (GitHub/GitLab/Bitbucket)
   - Select the repository containing this project

3. **Configure the Service**
   - **Name**: `wordle-optimizer-api` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or `./` if needed)
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```bash
     uvicorn api.api:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Free tier is fine for testing

4. **Environment Variables** (Optional)
   - No environment variables required for basic setup
   - If you want to restrict CORS, add:
     - Key: `ALLOWED_ORIGINS`
     - Value: `https://yourdomain.com`

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your API
   - Wait for the build to complete (usually 2-5 minutes)

6. **Get Your API URL**
   - Once deployed, you'll get a URL like: `https://wordle-optimizer-api.onrender.com`
   - The API will be available at this URL

### Option 2: Using render.yaml (Infrastructure as Code)

If you prefer to use the `render.yaml` file:

1. **Push render.yaml to your repository**
   - The `render.yaml` file is already in the root directory

2. **Create a Blueprint**
   - In Render dashboard, click "New +" → "Blueprint"
   - Connect your repository
   - Render will automatically detect and use `render.yaml`

3. **Deploy**
   - Render will create the service based on the YAML configuration

## Post-Deployment

### Test Your API

Once deployed, test the API:

```bash
# Health check
curl https://your-api-url.onrender.com/health

# Create a session
curl -X POST https://your-api-url.onrender.com/sessions

# Get suggestions
curl -X POST "https://your-api-url.onrender.com/sessions/{session_id}/suggestions?n=5"
```

### Access API Documentation

- **Swagger UI**: `https://your-api-url.onrender.com/docs`
- **ReDoc**: `https://your-api-url.onrender.com/redoc`

## Important Notes

### Free Tier Limitations

- **Spinning down**: Free tier services spin down after 15 minutes of inactivity
- **First request**: The first request after spin-down may take 30-60 seconds
- **Cold starts**: Consider upgrading to a paid plan for production use

### File Paths

The API uses relative paths to find the word lists:
- `words/words.txt` - All valid guesses
- `words/answers.txt` - Possible answers

Make sure these files are committed to your repository.

### CORS Configuration

The API currently allows all origins (`*`). For production:

1. Update `api/api.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Your frontend domain
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. Or use environment variable:
   ```python
   import os
   allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
   app.add_middleware(
       CORSMiddleware,
       allow_origins=allowed_origins,
       ...
   )
   ```

### Session Storage

Sessions are stored in-memory and will be lost on:
- Service restart
- Deployment
- After 15 minutes of inactivity (free tier)

For production, consider:
- Using Redis for session storage
- Implementing session persistence
- Using a database

## Troubleshooting

### Build Fails

1. **Check requirements.txt**: Make sure all dependencies are listed
2. **Check Python version**: Render uses Python 3.11 by default
3. **Check logs**: View build logs in Render dashboard

### API Returns 500 Errors

1. **Check file paths**: Ensure `words/words.txt` and `words/answers.txt` exist
2. **Check logs**: View runtime logs in Render dashboard
3. **Test locally**: Make sure it works locally first

### Slow Response Times

1. **Cold starts**: First request after spin-down is slow (free tier)
2. **Upgrade plan**: Consider paid plan for better performance
3. **Optimize code**: Check for any performance bottlenecks

## Next Steps

1. **Update your Next.js app** to use the Render API URL
2. **Set up environment variables** in your Next.js app:
   ```env
   NEXT_PUBLIC_API_URL=https://your-api-url.onrender.com
   ```
3. **Test the integration** between your frontend and API
4. **Monitor usage** in Render dashboard

## Example Next.js Integration

```typescript
// In your Next.js app
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://your-api-url.onrender.com';

// Create session
const createSession = async () => {
  const res = await fetch(`${API_URL}/sessions`, { method: 'POST' });
  return res.json();
};

// Get suggestions
const getSuggestions = async (sessionId: string, n: number = 5) => {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/suggestions?n=${n}`, {
    method: 'POST'
  });
  return res.json();
};
```

## Support

- Render Documentation: https://render.com/docs
- Render Community: https://community.render.com
- API Documentation: https://your-api-url.onrender.com/docs

