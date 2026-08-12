@echo off
python -m pip install -r requirements.txt
start cmd /k "uvicorn api:app --reload --port 8000"
streamlit run app.py
