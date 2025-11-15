# Member Messages Q&A System

A simple API that answers natural language questions about member messages using GPT-4. Ask things like "When is Layla going to London?" and get intelligent answers.

**Live Demo**: `[YOUR DEPLOYED URL HERE]`  
**Demo Video**: [Optional - Add Loom link]

---

## What It Does

This system reads 3,349 messages from 10 members and answers questions about their plans, preferences, and activities. It uses retrieval-augmented generation (RAG) with GPT-4 to understand context and generate accurate answers.

### Example Questions

```bash
# Question 1: When is Layla planning her trip to London?
curl -X POST https://your-app.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "When is Layla planning her trip to London?"}'

# Question 2: How many cars does Vikram Desai have?
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many cars does Vikram Desai have?"}'

# Question 3: What are Amira's favorite restaurants?
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are Amira'\''s favorite restaurants?"}'
```

**Response format**:
```json
{
  "answer": "Based on Layla's messages, she is planning a trip to London..."
}
```

---

## Quick Start

**Requirements**: Python 3.11+, OpenAI API key

```bash
# 1. Clone and install
git clone https://github.com/yourusername/qa-system.git
cd qa-system
pip install -r requirements.txt

# 2. Add your API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-proj-...

# 3. Run
python app.py
```

The API runs at `http://localhost:8080`. Test it:

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "When is Layla planning her trip to London?"}'
```

---

## API Endpoints

### `POST /ask`
Ask a question, get an answer.

**Request**: `{"question": "..."}`  
**Response**: `{"answer": "..."}`  
**Status codes**: 200 (success), 400 (bad request), 500 (error)

### `GET /health`
Check if the system is running.

**Response**: `{"status": "healthy", "messages_loaded": 3349, "users_loaded": 10}`

### `GET /stats`
Get system statistics.

**Response**: Message counts, user list, LLM provider info.

---

## Bonus 1: Alternative Approaches Considered

I evaluated 5 different approaches before choosing RAG with LLM:

### 1. RAG with LLM (Selected) ✅
**How**: Retrieve relevant messages → Pass to GPT-4 → Generate answer

**Pros**: Handles complex reasoning, synthesizes info from multiple messages, robust to question variations

**Cons**: Requires API key, slower (1-3 sec), has API costs

**Why I chose it**: Best accuracy and can handle all types of questions from the requirements.

### 2. Rule-Based Pattern Matching
**How**: Regex patterns + spaCy NER

**Pros**: Fast (<100ms), no dependencies, works offline

**Cons**: Brittle, fails on variations, high maintenance

**Verdict**: Good for MVP, not production-ready.

### 3. Fine-Tuned BERT QA Model
**How**: Pre-trained SQuAD model for extractive QA

**Pros**: No API calls, fast inference

**Cons**: Can't synthesize across messages, struggles with "how many" questions

**Verdict**: Good middle ground but limited.

### 4. Knowledge Graph + SPARQL
**How**: Convert messages to triples → Query with SPARQL

**Pros**: Structured data, explainable

**Cons**: Complex pipeline, NL-to-SPARQL is hard, overkill for this dataset

**Verdict**: Great for large knowledge bases, too much here.

### 5. Elasticsearch + BM25
**How**: Index messages → Search with keywords

**Pros**: Fast, scalable

**Cons**: No semantic understanding, no reasoning

**Verdict**: Good for search, not for QA.

**Full details**: See [DESIGN.md](DESIGN.md)

---

## Bonus 2: Data Insights & Anomalies

I analyzed all 3,349 messages from the API. Here's what I found:

### Dataset Overview
- **Total messages**: 3,349
- **Users**: 10 members
- **Distribution**: Fairly balanced (288-365 messages per user)
- **Content**: Travel bookings, restaurant reservations, preferences

### Key Anomalies Identified

**1. API Intermittent Errors**
The API randomly returns 403/404/405 errors during pagination. I built retry logic with exponential backoff to handle this - successfully fetches all 3,349 messages despite the errors.

**2. Name Mismatch: "Amira" vs "Amina"**
The example question asks about "Amira" but the dataset has "Amina Van Den Berg". I added fuzzy name matching (Levenshtein distance with 75% threshold) to handle this. Now "Amira" correctly maps to "Amina".

**3. Implicit Information**
Some questions ask for data that's not explicitly stated:
- "How many cars does Vikram have?" → No message says "I have X cars"
- "What are favorite restaurants?" → No explicit favorites, must infer from context

The LLM handles this well by inferring from context or saying "I don't have enough information."

**4. Relative Dates**
Messages use relative dates ("next Monday", "this Friday") without absolute timestamps. The system includes message timestamps in context so the LLM can reason about timing.

**5. Uniform Message Lengths**
All messages are 46-88 characters (avg 65). Likely synthetic data or truncated messages. Doesn't affect functionality.

**Full analysis**: See [data_insights.md](data_insights.md)

---

## Deployment

### Option 1: Railway (Easiest, Free)
1. Sign up at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Add env var: `OPENAI_API_KEY`
4. Deploy → Get your public URL

### Option 2: Docker
```bash
docker build -t qa-system .
docker run -d -p 8080:8080 -e OPENAI_API_KEY=your-key qa-system
```

### Option 3: Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/qa-system
gcloud run deploy qa-system --image gcr.io/PROJECT_ID/qa-system \
  --set-env-vars OPENAI_API_KEY=your-key
```

Other options: Render, Fly.io, Vercel, PythonAnywhere (all have free tiers)

---

## Project Structure

```
qa-system/
├── app.py              # Flask API (main entry point)
├── qa_engine.py        # QA logic (RAG + LLM)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container config
├── .env.example        # Environment template
├── README.md           # This file
├── DESIGN.md           # Detailed design (Bonus 1)
└── data_insights.md    # Data analysis (Bonus 2)
```

---

## How It Works

**Architecture**: Flask API → Data fetcher (with retry logic) → QA Engine (RAG) → LLM (GPT-4)

**Key features**:
- Fetches all 3,349 messages on startup
- Fuzzy name matching (handles "Amira" → "Amina")
- Retry logic for API errors
- In-memory caching for fast responses
- Falls back to keyword matching if no API key

**Performance**:
- Startup: ~15-25 seconds (fetches all messages)
- Response time: 1-3 seconds with GPT-4, <100ms fallback mode
- Handles concurrent requests with gunicorn

**Tech stack**: Flask, OpenAI GPT-4, RapidFuzz, Docker, Gunicorn

---

## Configuration

Create a `.env` file:

```bash
API_BASE_URL=https://november7-730026606190.europe-west1.run.app/messages/
OPENAI_API_KEY=your-key-here
PORT=8080
DEBUG=False
```

---

## Source Data

**API**: https://november7-730026606190.europe-west1.run.app/docs

The system fetches member messages from this public API using pagination (`skip` and `limit` params) and handles intermittent errors with retry logic.

---

Built with Python, Flask, and GPT-4. Demonstrates RAG architecture, LLM integration, and production-ready API development.
