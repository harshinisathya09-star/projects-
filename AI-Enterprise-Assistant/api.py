from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from core import init_db, run_sql_query, generate_answer, split_text, build_index, retrieve, extract_pdf_text, ocr_pdf_text

app=FastAPI(title="AI Enterprise Assistant API", version="1.0")

class AskRequest(BaseModel):
    question:str

class SQLRequest(BaseModel):
    question:str

@app.get("/")
def root():
    return {"status":"online","service":"AI Enterprise Assistant"}

@app.get("/health")
def health():
    return {"status":"healthy"}

@app.post("/documents/upload")
async def upload(file:UploadFile=File(...)):
    Path("documents").mkdir(exist_ok=True)
    path=Path("documents")/file.filename
    path.write_bytes(await file.read())
    text=extract_pdf_text(str(path))
    if len(text.strip())<50: text=ocr_pdf_text(str(path))
    return {"filename":file.filename,"characters":len(text),"chunks":len(split_text(text))}

@app.post("/sql/query")
def sql(req:SQLRequest):
    query=run_sql_query(req.question,True)
    return {"sql":query}

@app.post("/chat")
def chat(req:AskRequest):
    return {"message":"Use the Streamlit UI to upload/index a document first; this endpoint is available for integration."}
