import streamlit as st

PRIMARY = "#16a34a"
PRIMARY_DARK = "#15803d"
SECONDARY = "#3b82f6"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#dc2626"
TEXT = "#065f46"
BACKGROUND = "#f0fdf4"
BORDER = "#a7f3d0"
LIGHT = "#ecfdf5"


def apply_orbe_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

    :root {
        --bg-1: #f8fafc;
        --bg-2: #e9f2f7;
        --ink-1: #0b2c3d;
        --ink-2: #123b4f;
        --accent: #e85d3f;
        --accent-2: #c6472c;
        --accent-warm: #f3b340;
        --card: #ffffff;
        --border: #cfe2ee;
        --shadow: 0 12px 28px rgba(12, 38, 55, 0.10);
        --radius: 16px;
    }

    /* ============================================================
       ORBE THEME - UI OVERHAUL
       ============================================================ */

    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: "Space Grotesk", "Segoe UI", Tahoma, sans-serif !important;
        font-size: 1.16rem !important;
        line-height: 1.55 !important;
        color: var(--ink-1) !important;
        background: radial-gradient(1100px 600px at 15% -10%, #ffffff 0%, var(--bg-1) 48%, var(--bg-2) 100%) !important;
    }

    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
            radial-gradient(120px 60px at 10% 10%, rgba(232, 93, 63, 0.10), transparent 60%),
            radial-gradient(140px 80px at 90% 15%, rgba(243, 179, 64, 0.12), transparent 60%),
            radial-gradient(200px 120px at 20% 90%, rgba(18, 59, 79, 0.10), transparent 60%);
        pointer-events: none;
        z-index: 0;
    }

    [data-testid="stAppViewContainer"] > .main {
        position: relative;
        z-index: 1;
    }

    h1 { font-size: 2.3rem !important; }
    h2 { font-size: 1.86rem !important; }
    h3 { font-size: 1.5rem !important; }
    h4 { font-size: 1.28rem !important; }

    h1,h2,h3,h4 {
        font-family: "Fraunces", "Space Grotesk", serif !important;
        color: var(--ink-2) !important;
        font-weight: 700 !important;
        margin-top: 0.36rem !important;
        margin-bottom: 0.34rem !important;
    }

    input, textarea, select {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 0.6rem 0.78rem !important;
        font-size: 1.08rem !important;
        background: #ffffff !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.6) !important;
    }

    input:focus, textarea:focus, select:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(232, 93, 63, 0.25) !important;
        border-color: var(--accent) !important;
    }

    label, .stTextInput label, .stSelectbox label {
        font-size: 1.02rem !important;
        font-weight: 600 !important;
        color: var(--ink-2) !important;
        margin-bottom: 0.18rem !important;
    }

    [data-testid="stContainer"] {
        border-radius: var(--radius) !important;
    }

    .stDataFrame, .stTable {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow) !important;
    }

    div.stButton > button, button[kind="primary"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;

        background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;

        font-size: 1.12rem !important;
        font-weight: 700 !important;

        padding: 0.7rem 1.1rem !important;
        min-height: 3.0rem !important;
        min-width: 0 !important;
        width: auto !important;

        text-align: center !important;
        white-space: nowrap !important;
        line-height: 1 !important;
        overflow: hidden !important;
        box-shadow: 0 8px 18px rgba(232, 93, 63, 0.20) !important;
        transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease !important;
    }

    div.stButton > button:hover {
        filter: saturate(1.05) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 24px rgba(232, 93, 63, 0.26) !important;
    }

    .small-icon-btn, button[title][aria-label] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;

        min-width: 3.0rem !important;
        max-width: 3.0rem !important;
        min-height: 2.9rem !important;
        padding: 0.38rem !important;
        font-size: 1.08rem !important;
        border-radius: 12px !important;
    }

    div.stButton > button > span, div.stButton > button > svg {
        display: inline-block !important;
        vertical-align: middle !important;
        line-height: 1 !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f4f8fb 100%) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] div.stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;

        background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;

        font-size: 1.16rem !important;
        font-weight: 700 !important;

        padding: 0.84rem 1.05rem !important;
        margin-top: 0.50rem !important;

        width: 100% !important;
        min-height: 3.3rem !important;
        box-shadow: 0 8px 16px rgba(232, 93, 63, 0.20) !important;
    }

    [data-testid="stSidebar"] div.stButton > button:hover {
        transform: translateY(-1px) !important;
    }

    [data-testid="stVerticalBlock"] {
        padding-top: 0.04rem !important;
        padding-bottom: 0.04rem !important;
        margin-bottom: 0.22rem !important;
    }

    details, summary {
        padding: 0.5rem 0.7rem !important;
        font-size: 1.04rem !important;
    }

    th, td {
        padding: 9px !important;
        font-size: 1.02rem !important;
    }

    [data-testid="stSidebar"] {
        font-size: 1.04rem !important;
    }

    footer { visibility: hidden !important; }

    </style>
    """, unsafe_allow_html=True)
