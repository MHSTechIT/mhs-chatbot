# Document-Based Q&A Voice Chatbot Backend

This is the customized backend for a Document-Based Q&A Chatbot, built with FastAPI, LangChain, **Groq (Llama 3)**, HuggingFaceEmbeddings, and PostgreSQL (`pgvector`). The chatbot securely answers questions strictly based on a provided dummy document (`company_info.txt`), enforcing information boundaries and blocking restricted queries.

## Tech Stack
- **Framework:** FastAPI
- **LLM Orchestration:** LangChain
- **LLM Model:** Groq API (`llama-3.1-8b-instant`) - Ultra-fast cloud inference
- **Embeddings Model:** `HuggingFaceEmbeddings` (`all-MiniLM-L6-v2`) - 100% Free
- **Vector Database:** PostgreSQL with `pgvector` (Includes Connection Pooling)

## Prerequisites
Ensure you have the following installed on your machine:
1. [Docker & Docker Compose](https://docs.docker.com/get-docker/) (for PostgreSQL Vector database)
2. [Python 3.9+](https://www.python.org/downloads/)
3. [Groq API Key](https://console.groq.com/keys) (Free)

## Step-by-Step Setup Guide

### 1. Configure the Environment
Create a `.env` file in the root of the backend directory and add your Groq API key along with the database URL.

```env
GROQ_API_KEY=your_groq_api_key_here
DB_CONNECTION=postgresql+psycopg://postgres:<YOUR_DB_PASSWORD>@db.<YOUR_PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

### 2. Setup Supabase (Postgres + pgvector)
1. In [Supabase Dashboard](https://supabase.com/dashboard) → your project → **Database** → enable the `vector` extension (pgvector).
2. In **Project Settings** → **Database**, copy the **Connection string** (URI) and set it as `DB_CONNECTION` in your `.env`. Use the **Session mode** password (or reset it if needed). Example:
   `postgresql+psycopg://postgres:YOUR_PASSWORD@db.mktzrhqaxxclisxckmed.supabase.co:5432/postgres?sslmode=require`

### 3. Setup the Python Environment
Create a virtual environment and install the required dependencies:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Ingest the Dummy Document
Run the ingestion script. This script reads `company_info.txt`, splits the text into chunks, generates vector embeddings using HuggingFace, and stores them in the PostgreSQL database.
```bash
python ingest.py
```
*Note: The first time you run this, it will download the HuggingFace embeddings model (~90MB).*

### 5. Start the FastAPI Server
Run the backend web server using `uvicorn`:
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

## Testing the API

You can test the API using tools like Postman, cURL, or the built-in Swagger UI.

### Option A: Swagger UI
Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) in your browser. You can execute requests directly from the UI.

### Option B: cURL Commands

**1. Normal Valid Question** (Information exists in document)
```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What are the company office hours?"}'
```
*Expected Output:*
```json
{
  "answer": "The office hours are Monday to Friday, 9:00 AM to 6:00 PM PST.",
  "type": "normal"
}
```

**2. Restricted Question** (Intercepted by Semantic Guardrail)
```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the company revenue?"}'
```
*Expected Output:*
```json
{
  "answer": "You do not have the privilege to access this information.",
  "type": "restricted"
}
```

**3. Not Found Question** (Information NOT in document)
```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Who is the CEO of the company?"}'
```
*Expected Output:*
```json
{
  "answer": "The requested information is not available.",
  "type": "not_found"
}
```
