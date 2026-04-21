def load_css():
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

    /* ── ROOT ── */
    :root {
        --bg:        #08080a;
        --surface:   #0f0f12;
        --border:    #1c1c22;
        --accent:    #e8003d;
        --accent2:   #ff6b35;
        --text:      #f0f0f0;
        --muted:     #555566;
        --green:     #00e676;
        --amber:     #ffab00;
        --red:       #ff1744;
    }

    /* ── BASE ── */
    .stApp {
        background: var(--bg) !important;
        color: var(--text);
        font-family: 'DM Sans', sans-serif;
    }

    /* hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border);
        padding-top: 0 !important;
    }
    section[data-testid="stSidebar"] > div { padding: 28px 20px; }

    .sidebar-logo {
        font-family: 'Syne', sans-serif;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text);
        border-bottom: 1px solid var(--border);
        padding-bottom: 18px;
        margin-bottom: 24px;
    }
    .sidebar-logo span { color: var(--accent); }

    .sidebar-label {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 8px;
    }

    /* inputs */
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextArea textarea {
        background: var(--bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus-within > div,
    .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* button */
    .stButton > button {
        background: var(--accent) !important;
        color: white !important;
        border: none !important;
        border-radius: 0 !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 12px !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        font-weight: 500 !important;
        padding: 14px 20px !important;
        width: 100% !important;
        transition: background 0.2s ease, transform 0.1s ease !important;
        cursor: pointer !important;
    }
    .stButton > button:hover {
        background: #c4002e !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ── HEADER ── */
    .argus-header {
        padding: 48px 0 32px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 40px;
    }
    .argus-wordmark {
        font-family: 'Syne', sans-serif;
        font-size: 72px;
        font-weight: 800;
        letter-spacing: -3px;
        line-height: 1;
        color: var(--text);
        margin: 0;
    }
    .argus-wordmark .dot { color: var(--accent); }
    .argus-tagline {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--muted);
        margin-top: 10px;
    }

    /* ── LOADER ANIMATION ── */
    @keyframes pulse-bar {
        0%   { width: 0%; opacity: 1; }
        80%  { width: 100%; opacity: 1; }
        100% { width: 100%; opacity: 0; }
    }
    @keyframes blink-dot {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0; }
    }
    .loading-wrap {
        padding: 48px 0;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .loading-label {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--muted);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .blink { animation: blink-dot 1s infinite; color: var(--accent); }
    .progress-track {
        height: 2px;
        background: var(--border);
        width: 100%;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        animation: pulse-bar 2s ease-in-out infinite;
    }

    /* ── METRICS ── */
    .metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1px;
        background: var(--border);
        border: 1px solid var(--border);
        margin-bottom: 40px;
    }
    .metric-cell {
        background: var(--surface);
        padding: 24px 20px;
    }
    .metric-key {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 10px;
    }

    /* Streamlit column metric wrappers */
    div[data-testid="column"] {
        border-right: 1px solid var(--border);
        padding: 20px 16px !important;
    }
    div[data-testid="column"]:last-child {
        border-right: none;
    }
    .metric-val {
        font-family: 'Syne', sans-serif;
        font-size: 36px;
        font-weight: 800;
        color: var(--text);
        line-height: 1;
        margin-top: 6px;
    }
    .metric-val.verdict-entailment { color: var(--green); }
    .metric-val.verdict-weak_support { color: var(--amber); }
    .metric-val.verdict-neutral { color: var(--amber); }
    .metric-val.verdict-contradiction { color: var(--red); }
    .metric-val.verdict-no_support { color: var(--red); }

    /* trust bar inline */
    .trust-bar-wrap { margin-top: 8px; }
    .trust-track {
        height: 3px;
        background: var(--border);
        width: 100%;
        margin-top: 4px;
    }
    .trust-fill { height: 100%; transition: width 1s ease; }

    /* ── SECTION LABEL ── */
    .section-label {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--muted);
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
    }

    /* ── ANSWER ── */
    .answer-block {
        border-left: 3px solid var(--accent);
        padding: 24px 28px;
        background: var(--surface);
        font-size: 18px;
        font-weight: 300;
        line-height: 1.8;
        color: var(--text);
        margin-bottom: 40px;
        letter-spacing: 0.01em;
    }

    /* ── EVIDENCE ── */
    .evidence-item {
        display: flex;
        gap: 16px;
        padding: 16px 0;
        border-bottom: 1px solid var(--border);
        align-items: flex-start;
    }
    .ev-index {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--accent);
        min-width: 28px;
        padding-top: 1px;
    }
    .ev-text {
        font-size: 14px;
        line-height: 1.7;
        color: #aaaabc;
        font-weight: 300;
    }

    /* ── SPINNER OVERRIDE ── */
    .stSpinner > div { border-top-color: var(--accent) !important; }

    /* ── SCROLL ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); }
    </style>
    """