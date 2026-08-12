import os, re, sqlite3
from pathlib import Path
import fitz
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

load_dotenv()

def gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "AI API key is not configured. Add GEMINI_API_KEY to .env and restart the app."
    try:
        from google import genai
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Gemini error: {e}"

def extract_pdf_text(path):
    doc = fitz.open(path)
    pages=[]
    for i,p in enumerate(doc):
        txt=p.get_text("text")
        if txt.strip():
            pages.append(f"[Page {i+1}]\n{txt}")
    return "\n\n".join(pages)

def ocr_pdf_text(path):
    try:
        import pytesseract
        from PIL import Image
        doc=fitz.open(path)
        out=[]
        for i,p in enumerate(doc):
            pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5))
            img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
            out.append(f"[Page {i+1}]\n"+pytesseract.image_to_string(img))
        return "\n\n".join(out)
    except Exception as e:
        return f"OCR unavailable: {e}"

def split_text(text, size=900, overlap=120):
    text=text.strip()
    if not text: return []
    chunks=[]
    start=0
    while start < len(text):
        chunks.append(text[start:start+size])
        start += size-overlap
    return chunks

def build_index(chunks):
    vectorizer=TfidfVectorizer(stop_words="english")
    matrix=vectorizer.fit_transform(chunks)
    return (vectorizer,matrix)

def retrieve(question,index,chunks,k=4):
    if not chunks or index is None: return []
    vectorizer,matrix=index
    q=vectorizer.transform([question])
    scores=cosine_similarity(q,matrix)[0]
    ids=scores.argsort()[-k:][::-1]
    return [chunks[i] for i in ids if scores[i] > 0] or chunks[:k]

def generate_answer(question, context, sources):
    joined="\n\n".join(context)
    prompt=f"""You are an enterprise assistant. Answer ONLY from the supplied context.
If the answer is not present, say: "I could not find this information in the uploaded document."
Be concise and cite the source filename and page label when available.

CONTEXT:
{joined}

QUESTION:
{question}
"""
    ans=gemini(prompt)
    return ans + f"\n\n**Source document:** {', '.join(sources) if sources else 'N/A'}"

def init_db():
    conn=sqlite3.connect("enterprise.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY, product TEXT, department TEXT,
        amount REAL, month TEXT)""")
    count=conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    if count==0:
        rows=[
            (1,"Laptop","IT",50000,"July"),(2,"Phone","Sales",30000,"July"),
            (3,"Monitor","IT",25000,"August"),(4,"Laptop","Sales",60000,"August"),
            (5,"Tablet","Sales",40000,"September"),(6,"Monitor","IT",35000,"September")
        ]
        conn.executemany("INSERT INTO sales VALUES(?,?,?,?,?)",rows)
        conn.commit()
    return conn

def run_sql_query(question, return_sql=False):
    prompt=f"""Convert this user question into ONE safe SQLite SELECT query.
Table: sales(id, product, department, amount, month)
Return SQL only. Never use INSERT, UPDATE, DELETE, DROP, ALTER or PRAGMA.
Question: {question}"""
    sql=gemini(prompt).strip().replace("```sql","").replace("```","").strip()
    if not re.match(r"(?is)^select\b",sql):
        # deterministic fallback for common demo questions
        q=question.lower()
        if "july" in q and ("total" in q or "sales" in q):
            sql="SELECT SUM(amount) AS total_sales FROM sales WHERE month='July';"
        elif "highest" in q or "best" in q:
            sql="SELECT product, SUM(amount) AS total_sales FROM sales GROUP BY product ORDER BY total_sales DESC LIMIT 1;"
    return sql

def generate_report(df):
    summary=df.groupby("month",as_index=False)["amount"].sum()
    prompt=f"""Create a professional executive business report from this sales data.
Include Executive Summary, Key Metrics, Key Findings, and Recommendations.
Data:
{summary.to_string(index=False)}
Overall sales: {df['amount'].sum():.2f}
"""
    return gemini(prompt)

def evaluate_answer(answer, expected):
    words=[w.lower() for w in re.findall(r"\w+",expected) if len(w)>2]
    if not words: return 0,"Needs review"
    found=sum(1 for w in words if w in answer.lower())
    score=100*found/len(words)
    return score, "PASS" if score>=70 else "NEEDS REVIEW"
