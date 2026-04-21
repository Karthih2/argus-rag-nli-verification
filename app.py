import streamlit as st
from src.main import run_pipeline

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="ARGUS | RAG Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------
# RED + BLACK PROFESSIONAL CSS
# ---------------------------------------------------
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root{
        --bg:#050505;
        --panel:#0d0d0f;
        --panel2:#121214;
        --line:#1d1d22;
        --red:#ff003c;
        --red2:#b8002c;
        --text:#f5f5f5;
        --muted:#7a7a85;
        --green:#00e676;
        --amber:#ffb300;
    }

    html, body, .stApp {
        background: var(--bg);
        color: var(--text);
        font-family: 'Inter', sans-serif;
    }

    #MainMenu, footer, header {
        visibility:hidden;
    }

    /* Sidebar */
    section[data-testid="stSidebar"]{
        background: linear-gradient(180deg,#090909,#111111);
        border-right:1px solid var(--line);
    }

    .sidebar-logo{
        font-family:'JetBrains Mono', monospace;
        font-size:28px;
        font-weight:700;
        letter-spacing:-1px;
        color:#fff;
        padding-bottom:18px;
        border-bottom:1px solid var(--line);
        margin-bottom:28px;
    }

    .sidebar-logo span{
        color:var(--red);
    }

    .sidebar-label{
        font-family:'JetBrains Mono', monospace;
        font-size:10px;
        letter-spacing:2px;
        text-transform:uppercase;
        color:var(--muted);
        margin-bottom:8px;
        margin-top:8px;
    }

    /* Inputs */
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div{
        background:var(--panel) !important;
        color:#fff !important;
        border:1px solid var(--line) !important;
        border-radius:4px !important;
        font-size:14px !important;
    }

    .stTextArea textarea:focus,
    .stSelectbox div[data-baseweb="select"] > div:focus-within{
        border:1px solid var(--red) !important;
        box-shadow:none !important;
    }

    /* Button */
    .stButton > button{
        width:100%;
        background:linear-gradient(90deg,var(--red),var(--red2));
        color:#fff;
        border:none;
        border-radius:4px;
        height:46px;
        font-weight:700;
        letter-spacing:1px;
        transition:0.2s ease;
    }

    .stButton > button:hover{
        transform:translateY(-1px);
        filter:brightness(1.1);
    }

    /* Header */
    .hero{
        padding:8px 0 25px 0;
        border-bottom:1px solid var(--line);
        margin-bottom:28px;
    }

    .hero-title{
        font-size:54px;
        font-weight:800;
        letter-spacing:-2px;
        margin-bottom:4px;
    }

    .hero-title span{
        color:var(--red);
    }

    .hero-sub{
        color:var(--muted);
        font-size:14px;
        letter-spacing:0.3px;
    }

    /* Metrics */
    .metric-box{
        background:var(--panel);
        border:1px solid var(--line);
        padding:18px;
        border-radius:4px;
        min-height:118px;
    }

    .metric-key{
        font-family:'JetBrains Mono', monospace;
        font-size:10px;
        color:var(--muted);
        text-transform:uppercase;
        letter-spacing:1.5px;
        margin-bottom:12px;
    }

    .metric-val{
        font-size:30px;
        font-weight:700;
        line-height:1;
    }

    .good{color:var(--green);}
    .warn{color:var(--amber);}
    .bad{color:var(--red);}

    .mini{
        font-size:13px;
        color:var(--muted);
    }

    .track{
        width:100%;
        height:4px;
        background:#1c1c1f;
        margin-top:14px;
        overflow:hidden;
        border-radius:2px;
    }

    .fill{
        height:100%;
        border-radius:2px;
    }

    /* Sections */
    .section-title{
        margin-top:28px;
        margin-bottom:14px;
        font-family:'JetBrains Mono', monospace;
        font-size:11px;
        color:var(--muted);
        letter-spacing:2px;
        text-transform:uppercase;
    }

    .answer-box{
        background:var(--panel);
        border:1px solid var(--line);
        border-left:3px solid var(--red);
        padding:22px;
        border-radius:4px;
        font-size:17px;
        line-height:1.8;
    }

    .evidence-box{
        background:var(--panel2);
        border:1px solid var(--line);
        border-radius:4px;
        padding:16px;
        margin-bottom:12px;
    }

    .ev-id{
        font-family:'JetBrains Mono', monospace;
        color:var(--red);
        font-size:11px;
        margin-bottom:8px;
    }

    .ev-text{
        color:#d8d8d8;
        font-size:14px;
        line-height:1.7;
    }

    .status-box{
        background:var(--panel);
        border:1px solid var(--line);
        padding:18px;
        border-radius:4px;
        color:#bbb;
    }

    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
with st.sidebar:

    st.markdown(
        '<div class="sidebar-logo">ARGUS<span>.</span></div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-label">Domain</div>', unsafe_allow_html=True)
    domain = st.selectbox("", ["nasa", "anime"], label_visibility="collapsed")

    st.markdown('<div class="sidebar-label">Query Input</div>', unsafe_allow_html=True)
    query = st.text_area(
        "",
        height=190,
        placeholder="Ask anything...",
        label_visibility="collapsed"
    )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    run = st.button("RUN ARGUS")

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-title">ARGUS<span>.</span></div>
    <div class="hero-sub">Verified Retrieval-Augmented Intelligence System</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# IDLE
# ---------------------------------------------------
if not run:
    st.markdown(
        '<div class="status-box">SYSTEM READY · ENTER QUERY TO START ANALYSIS</div>',
        unsafe_allow_html=True
    )
    st.stop()

if not query.strip():
    st.warning("Please enter a query.")
    st.stop()

# ---------------------------------------------------
# LOADING
# ---------------------------------------------------
with st.spinner("Running ARGUS pipeline..."):
    result = run_pipeline(query=query, domain=domain)

# ---------------------------------------------------
# DATA
# ---------------------------------------------------
answer = result.get("answer", "No answer.")
verdict = result.get("verdict", "unknown").lower()
confidence = result.get("confidence", 0.0)
trust_score = result.get("trust_score", 0)
latency = result.get("latency", 0)
evidence = result.get("evidence", [])

# Colors
bar = "#00e676" if trust_score >= 80 else "#ffb300" if trust_score >= 50 else "#ff003c"

if verdict in ["entailment", "supported"]:
    verdict_class = "good"
elif verdict in ["neutral", "weak_support"]:
    verdict_class = "warn"
else:
    verdict_class = "bad"

# ---------------------------------------------------
# METRICS
# ---------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-key">Verdict</div>
        <div class="metric-val {verdict_class}">{verdict.upper()}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-key">Trust Score</div>
        <div class="metric-val">{trust_score}<span class="mini"> /100</span></div>
        <div class="track"><div class="fill" style="width:{trust_score}%;background:{bar};"></div></div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-key">Confidence</div>
        <div class="metric-val">{confidence:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-key">Latency</div>
        <div class="metric-val">{latency}<span class="mini"> s</span></div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# ANSWER
# ---------------------------------------------------
st.markdown('<div class="section-title">Generated Response</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="answer-box">{answer}</div>',
    unsafe_allow_html=True
)

# ---------------------------------------------------
# EVIDENCE
# ---------------------------------------------------
if evidence:
    st.markdown('<div class="section-title">Supporting Evidence</div>', unsafe_allow_html=True)

    for i, ev in enumerate(evidence, 1):

        txt = ev.get("sentence", "") if isinstance(ev, dict) else str(ev)

        st.markdown(f"""
        <div class="evidence-box">
            <div class="ev-id">SOURCE_{i:02d}</div>
            <div class="ev-text">{txt}</div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------
# DEBUG
# ---------------------------------------------------
with st.expander("Inspect Raw Telemetry"):
    st.json(result)