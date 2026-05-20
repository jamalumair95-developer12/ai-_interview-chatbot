# 🚀 Deployment Guide - AI Interview Chatbot

## Vercel Deployment (Recommended)

This project is now fully configured for Vercel deployment with a Flask API backend.

### Prerequisites
- Vercel account ([https://vercel.com](https://vercel.com))
- GitHub repository with this code
- Groq API Key ([https://console.groq.com](https://console.groq.com))

### Step-by-Step Deployment

#### 1. Prepare Your Repository
```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

#### 2. Connect to Vercel
1. Go to [https://vercel.com](https://vercel.com)
2. Click "New Project"
3. Select your GitHub repository
4. Select "Other" as the framework
5. Click "Deploy"

#### 3. Configure Environment Variables
In the Vercel project settings, add:

| Variable Name | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API Key |

#### 4. Deploy
The deployment will automatically:
- Install dependencies from `requirements.txt`
- Run the Flask app from `api/index.py`
- Configure Python 3.11 runtime
- Set max duration to 30 seconds per request

### Post-Deployment

#### Test the API
```bash
# Health check
curl https://your-project.vercel.app/health

# Get API info
curl https://your-project.vercel.app/

# Send a chat message
curl -X POST https://your-project.vercel.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about yourself", "session_id": "user123"}'
```

#### Available Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Home page with API documentation |
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Send interview question |
| `POST` | `/api/upload-resume` | Upload and index resume |

### Local Development

#### Run as Streamlit App
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Run Streamlit app
streamlit run app.py
```

#### Run as Flask API
```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python api/index.py
# Or
flask --app api.index run
```

### Troubleshooting

#### Error: "app does not export a top-level variable"
✅ **Fixed** - The `api/index.py` file now properly exports the Flask `app` variable.

#### Environment Variables Not Loading
1. Check Vercel project settings for environment variables
2. Ensure `GROQ_API_KEY` is set
3. Redeploy after changing variables: `vercel --prod`

#### Chunking Size Error
If you get an error about chunk size on Vercel, ensure your `vercel.json` has the correct `maxDuration` setting (set to 30 seconds).

### Project Structure

```
ai_interview_chatbot-using-groq/
├── api/
│   ├── __init__.py
│   ├── index.py          ← Vercel entry point (Flask app)
│   └── routes.py
├── chatbot/              ← LangChain interview chains
├── ui/                   ← Streamlit components
├── utils/                ← Helper functions
├── app.py                ← Streamlit app (local)
├── requirements.txt      ← Python dependencies
├── vercel.json          ← Vercel configuration
└── .vercelignore        ← Files to exclude from Vercel
```

### Important Notes

1. **Streamlit App**: The local Streamlit app (`app.py`) is still available for development
2. **Flask API**: The Vercel deployment uses Flask (`api/index.py`) for serverless compatibility
3. **Environment**: Make sure `GROQ_API_KEY` is set in your Vercel project
4. **Max Duration**: Groq API calls may take 2-5 seconds, so 30 seconds is optimal

### Monitoring

View deployment logs in Vercel:
1. Go to your Vercel project dashboard
2. Click on "Deployments"
3. Select the latest deployment
4. View "Logs" for real-time debugging

### Redeploy

To redeploy manually:
```bash
# With Vercel CLI
vercel --prod

# Or push to GitHub
git push origin main  # Auto-deploys if connected
```

---

**Need help?** 
- Check [Vercel Python Docs](https://vercel.com/docs/functions/runtimes/python)
- Review [Groq API Docs](https://console.groq.com/docs)
- Check Vercel deployment logs for errors
