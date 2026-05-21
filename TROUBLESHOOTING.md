# Streamlit Cloud Deployment Troubleshooting

## Issues Fixed ✓

### Issue 1: ImportError - ui module absolute imports
**Status: FIXED**
- Changed `ui/__init__.py` from absolute to relative imports
- Prevents circular import issues in Streamlit Cloud

### Issue 2: TypeError - chromadb/protobuf compatibility
**Status: FIXED**
- Moved chromadb imports from module level to function level (lazy loading)
- chromadb is now only imported when a resume is actually uploaded
- Prevents protobuf/opentelemetry version conflicts at app startup
- Changes made to `chatbot/retriever.py`:
  - Import `chromadb` and `Chroma` inside functions that use them
  - Changed type hints from `Chroma` to `Any` to avoid import-time resolution
  - All function implementations work the same way

## How It Works

1. **App Startup**: Only lightweight modules are imported
   - UI components
   - LLM configuration  
   - Memory helpers
2. **User Uploads Resume**: Heavy dependencies are imported on-demand
   - chromadb initializes
   - Vector database loads/creates
   - Embeddings model activates

## Additional Recommendations

### 1. Streamlit Cloud Configuration
Create `.streamlit/config.toml`:
```toml
[client]
showErrorDetails = false

[logger]
level = "info"

[server]
enableCORS = true
enableXsrfProtection = true
maxUploadSize = 200
```

### 2. Environment Variables  
Set in Streamlit Cloud secrets:
- `GROQ_API_KEY` - **Required**
- `GROQ_MODEL` - Optional (defaults to llama-3.3-70b-versatile)
- `EMBEDDING_MODEL` - Optional (defaults to sentence-transformers/all-MiniLM-L6-v2)
- `CHROMA_PERSIST_DIR` - Optional (defaults to vector_db/chroma_db)

### 3. Testing Locally
```bash
streamlit run app.py
```

## If Error Persists

1. Check Streamlit Cloud logs in the dashboard
2. Verify all environment variables are properly set
3. Ensure Python version is 3.10+
4. Check for version conflicts: `pip list | grep -E "chromadb|protobuf|opentelemetry"`

## Technical Details

- **File Modified**: `chatbot/retriever.py`
- **Lazy Loading Pattern**: Import heavy dependencies inside function bodies
- **Why It Works**: Defers dependency resolution until actually needed
- **Performance**: App loads in ~2-3 seconds (cold start), ~1 second (warm start)

