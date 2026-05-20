"""
Vercel deployment entry point for AI Interview Chatbot.
Exports Flask app that Vercel expects.
"""

from flask import Flask, jsonify, request, render_template_string
import sys
from pathlib import Path
import os

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Create Flask app
app = Flask(__name__, static_folder=str(ROOT / "assets"), static_url_path="/assets")

# Load environment variables
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Import chatbot components
from chatbot.chains import InterviewChainManager
from utils.helpers import ensure_directories, read_resume_file, setup_logging

setup_logging()
ensure_directories()


@app.route("/", methods=["GET"])
def index():
    """Serve home page with info about the Streamlit app."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Interview Chatbot</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 {
                color: #333;
                margin: 0 0 20px 0;
            }
            p {
                color: #666;
                line-height: 1.6;
                margin: 10px 0;
            }
            .status {
                background: #f0f9ff;
                border-left: 4px solid #0ea5e9;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }
            .api-info {
                background: #f5f5f5;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                font-family: monospace;
            }
            .endpoint {
                padding: 8px 0;
                color: #333;
            }
            .method {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 8px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✨ AI Interview Chatbot</h1>
            <p>Your AI-powered interview preparation companion using Groq API and LangChain.</p>
            
            <div class="status">
                <strong>Status:</strong> ✅ API Server is running on Vercel
            </div>
            
            <h2>API Endpoints</h2>
            <div class="api-info">
                <div class="endpoint">
                    <span class="method">GET</span> /health — Health check
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /api/chat — Send interview question
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /api/upload-resume — Upload resume for indexing
                </div>
            </div>
            
            <h2>Local Development</h2>
            <p>To run the Streamlit app locally:</p>
            <div class="api-info">
                streamlit run app.py
            </div>
            
            <h2>Tech Stack</h2>
            <ul>
                <li>Framework: Flask (API) + Streamlit (UI)</li>
                <li>LLM: Groq (Free high-speed inference)</li>
                <li>Vector DB: ChromaDB</li>
                <li>Embeddings: Sentence Transformers</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "resume-ai-chatbot"}), 200


@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat endpoint for interview questions."""
    try:
        data = request.get_json()
        question = data.get("question", "")
        session_id = data.get("session_id", "default")
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        # Initialize chain manager
        chain_manager = InterviewChainManager()
        response = chain_manager.generate_response(question, session_id)
        
        return jsonify({
            "session_id": session_id,
            "question": question,
            "response": response,
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    """Resume upload and indexing endpoint."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        session_id = request.form.get("session_id", "default")
        
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        
        # Read and process resume
        resume_text = read_resume_file(file.filename, file.read())
        
        # Initialize chain manager and index resume
        chain_manager = InterviewChainManager()
        chain_manager.index_resume(resume_text, session_id)
        
        return jsonify({
            "status": "success",
            "message": "Resume indexed successfully",
            "session_id": session_id
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "status": "error"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({
        "error": "Internal server error",
        "status": "error"
    }), 500


if __name__ == "__main__":
    # For local development
    app.run(debug=True, port=5000)
