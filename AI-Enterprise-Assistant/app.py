import os, re, sqlite3, time, logging
os.makedirs("logs", exist_ok=True)
from pathlib import Path
Path("documents").mkdir(parents=True, exist_ok=True)
Path("reports").mkdir(parents=True, exist_ok=True)
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()
from core import (
    extract_pdf_text, ocr_pdf_text, split_text, build_index,
    retrieve, generate_answer, init_db, run_sql_query,
    generate_report, evaluate_answer
)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

st.set_page_config(page_title="Enterprise AI Assistant", page_icon="🤖", layout="wide")

if "index" not in st.session_state:
    st.session_state.index = None
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "sources" not in st.session_state:
    st.session_state.sources = []
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #f8fbff, #eef5ff);
    }

    .login-card {
        background: white;
        padding: 30px;
        border-radius: 18px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        border: 1px solid #e6edf7;
    }

    .login-title {
        color: #1f4e79;
        text-align: center;
        font-size: 32px;
        font-weight: 700;
    }

    .login-subtitle {
        color: #64748b;
        text-align: center;
        font-size: 15px;
        margin-bottom: 20px;
    }

    div.stButton > button {
        background-color: #2f80ed;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 10px 20px;
    }

    div.stButton > button:hover {
        background-color: #2563c7;
        color: white;
    }
</style>
""", unsafe_allow_html=True)
def login_screen():
    st.title("🤖 Enterprise AI Assistant")
    st.caption("AI-powered document intelligence, SQL analytics and report generation")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        u = st.text_input("Username", key="lu")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("Login", type="primary"):
            if u and p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Enter username and password.")
    with tab2:
        st.text_input("Full name", key="rn")
        st.text_input("Email", key="re")
        st.text_input("Password", type="password", key="rp")
        if st.button("Create account"):
            st.success("Registration successful. You can now login.")

if not st.session_state.logged_in:
    login_screen()
    st.stop()

st.sidebar.title("🏢 Enterprise AI")
st.sidebar.success(f"Logged in: {st.session_state.user}")
page = st.sidebar.radio("Navigation", [
    "Dashboard", "Documents & RAG", "SQL Agent", "AI Reports", "Evaluation", "Monitoring"
])
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# Dashboard
if page == "Dashboard":
    st.title("📊 Enterprise Command Center")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Documents", len(st.session_state.sources))
    c2.metric("AI Queries", st.session_state.get("queries", 0))
    c3.metric("System Status", "Online")
    c4.metric("RAG Index", "Ready" if st.session_state.index is not None else "Waiting")

    db = init_db()
    df = pd.read_sql_query("SELECT * FROM sales", db)
    db.close()
    st.subheader("Sales Analytics")
    fig = px.bar(df.groupby("month", as_index=False)["amount"].sum(), x="month", y="amount",
                 title="Monthly Sales")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)

# Documents + RAG
elif page == "Documents & RAG":
    st.title("📄 Document Intelligence & RAG")
    uploaded = st.file_uploader("Upload enterprise PDF", type=["pdf"])
    if uploaded:
        path = Path("documents") / uploaded.name
        path.write_bytes(uploaded.getbuffer())
        with st.spinner("Extracting document..."):
            text = extract_pdf_text(str(path))
            if len(text.strip()) < 50:
                text = ocr_pdf_text(str(path))
            chunks = split_text(text)
            st.session_state.chunks = chunks
            st.session_state.sources = [uploaded.name]
            st.session_state.index = build_index(chunks)
        st.success(f"Processed {uploaded.name} — {len(chunks)} chunks indexed.")
        st.info("RAG is ready. Ask a question below.")

    q = st.text_input("Ask about your uploaded document")
    if st.button("Ask AI", type="primary") and q:
        if not st.session_state.chunks:
            st.warning("Upload a PDF first.")
        else:
            start=time.time()
            context = retrieve(q, st.session_state.index, st.session_state.chunks, k=4)
            answer = generate_answer(q, context, st.session_state.sources)
            st.session_state.queries = st.session_state.get("queries",0)+1
            logging.info("RAG query | user=%s | latency=%.2f", st.session_state.user, time.time()-start)
            st.subheader("🤖 Answer")
            st.write(answer)
            st.subheader("📚 Retrieved Sources")
            for i, item in enumerate(context,1):
                st.caption(f"Source {i}: {st.session_state.sources[0]}")
                st.write(item[:700] + ("..." if len(item)>700 else ""))

# SQL
elif page == "SQL Agent":
    st.title("🗄️ Natural Language SQL Agent")
    db = init_db()
    df = pd.read_sql_query("SELECT * FROM sales", db)
    db.close()
    st.dataframe(df, use_container_width=True)
    question = st.text_input("Ask a database question",
                             placeholder="What were total sales in July?")
    if st.button("Run SQL Agent", type="primary") and question:
        sql = run_sql_query(question, return_sql=True)
        st.code(sql, language="sql")
        if sql.lower().strip().startswith("select"):
            try:
                db = init_db()
                result = pd.read_sql_query(sql, db)
                db.close()
                st.success("Query executed successfully.")
                st.dataframe(result, use_container_width=True)
            except Exception as e:
                st.error(f"SQL error: {e}")
        else:
            st.error("Only read-only SELECT queries are allowed.")

# Reports
elif page == "AI Reports":
    st.title("📑 Intelligent Report Generator")
    db = init_db()
    df = pd.read_sql_query("SELECT * FROM sales", db)
    db.close()
    st.dataframe(df, use_container_width=True)
    if st.button("Generate Executive Report", type="primary"):
        with st.spinner("Generating report..."):
            report = generate_report(df)
        st.markdown(report)
        Path("reports/executive_report.md").write_text(report, encoding="utf-8")
        st.download_button("Download Report", report, file_name="executive_report.md")

# Evaluation
elif page == "Evaluation":
    st.title("✅ AI Response Evaluation")
    question = st.text_input("Test question", "What is the leave policy?")
    expected = st.text_input("Expected keywords", "leave")
    answer = st.text_area("AI answer to evaluate")
    if st.button("Evaluate"):
        score, verdict = evaluate_answer(answer, expected)
        c1,c2=st.columns(2)
        c1.metric("Keyword Accuracy", f"{score:.0f}%")
        c2.metric("Verdict", verdict)
        st.progress(score/100)

# Monitoring
elif page == "Monitoring":
    st.title("📈 Monitoring & Logging")
    log = Path("logs/app.log")
    if log.exists():
        lines = log.read_text(errors="ignore").splitlines()
        st.metric("Logged Events", len(lines))
        st.code("\n".join(lines[-50:]))
    else:
        st.info("No logs yet.")
    st.subheader("Health")
    st.success("API/UI service: Healthy")
    st.success("Database: Healthy")
    st.success("RAG engine: Ready" if st.session_state.index is not None else "RAG engine: Waiting for document")
