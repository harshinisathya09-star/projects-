# 🤖 AI-Powered Enterprise Assistant

A competition-ready MVP combining document intelligence, OCR, RAG question answering, natural-language SQL analytics, dashboards, AI reports, evaluation, monitoring and REST APIs.

## Features
- User login/register UI
- Enterprise PDF upload
- PDF text extraction
- OCR fallback for scanned PDFs
- Retrieval-Augmented Generation (TF-IDF retrieval + Gemini generation)
- Source-aware answers
- Natural-language SQL agent with SELECT-only protection
- Interactive sales dashboard
- AI executive report generation
- Basic response evaluation
- Application logging and health monitoring
- FastAPI REST API + Swagger
- Docker deployment

## Run locally
1. Create `.env` from `.env.example`.
2. Add your Gemini API key.
3. Install:
   `pip install -r requirements.txt`
4. Start:
   `streamlit run app.py`
5. API docs:
   `uvicorn api:app --reload --port 8000`
   Open `/docs`.

## Demo questions
RAG:
- What is the leave policy?
- What are the working hours?

SQL:
- What were total sales in July?
- Which product has the highest sales?

## Architecture
User → Streamlit → Document/OCR → Retrieval → Gemini → Answer
User → SQL Agent → Safe SELECT → SQLite → Analytics
All modules → Logs/Evaluation → Monitoring

## Security notes
- Keep `.env` out of GitHub.
- SQL agent permits only SELECT statements.
- Replace demo authentication with hashed passwords/JWT before production.
