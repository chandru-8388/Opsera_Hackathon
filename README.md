# Opsera_Hackathon

AI-powered failure log analysis demo — a minimal hackathon application that accepts log snippets, sends them to OpenAI GPT-4o-mini for root-cause analysis, and displays structured results in a Streamlit dashboard.

## Project Structure

```
.
├── app.py            # FastAPI backend — POST /analyze endpoint
├── dashboard.py      # Streamlit frontend — log input and results UI
└── requirements.txt  # Python dependencies
```

## Prerequisites

- Python 3.10+
- An OpenAI API key with access to GPT-4o-mini

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your OpenAI API key
export OPENAI_API_KEY=<your-api-key>  # On Windows: set OPENAI_API_KEY=<your-api-key>
```

## Running the Application

Open two terminal windows:

**Terminal 1 — FastAPI backend (port 8000):**
```bash
uvicorn app:app --reload
```

**Terminal 2 — Streamlit frontend (port 8501):**
```bash
streamlit run dashboard.py
```

Open your browser to [http://localhost:8501](http://localhost:8501).

## API Documentation

Interactive Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs) when the backend is running.

## Architecture

- **Backend**: FastAPI with Pydantic v2 for request/response validation and OpenAI Structured Outputs
- **Frontend**: Streamlit for a polished Python-native UI with zero HTML/CSS
- **AI**: OpenAI GPT-4o-mini via `.parse()` for schema-enforced structured responses
- **Communication**: Synchronous HTTP via the `requests` library (Streamlit → FastAPI)
