#!/bin/bash
python -m pip install -r requirements.txt
uvicorn api:app --reload --port 8000 &
streamlit run app.py
