# src/ui/helpers.py

import streamlit as st


# ==========================================================
# VERDICT COLORS
# ==========================================================
def get_verdict_color(verdict: str) -> str:
    verdict = verdict.lower()

    if verdict == "entailment":
        return "#00c853"   # green

    if verdict == "weak_support":
        return "#ff9100"   # orange

    if verdict == "neutral":
        return "#ffc107"   # amber

    if verdict == "contradiction":
        return "#ff1744"   # red

    if verdict == "no_support":
        return "#ff1744"

    return "#9e9e9e"


# ==========================================================
# VERDICT BADGE
# ==========================================================
def render_verdict_badge(verdict: str):
    color = get_verdict_color(verdict)

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:8px 14px;
            border:1px solid {color};
            color:{color};
            font-weight:700;
            font-size:14px;
            border-radius:4px;
            letter-spacing:0.5px;
            margin-bottom:10px;
        ">
            {verdict.upper()}
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# TRUST BAR
# ==========================================================
def render_trust_bar(score: int):
    score = max(0, min(score, 100))

    if score >= 80:
        color = "#00c853"
    elif score >= 50:
        color = "#ff9100"
    else:
        color = "#ff1744"

    st.markdown(
        f"""
        <div style="margin-bottom:10px;">
            <div style="
                background:#111;
                border:1px solid #222;
                height:16px;
                width:100%;
                overflow:hidden;
            ">
                <div style="
                    width:{score}%;
                    background:{color};
                    height:100%;
                "></div>
            </div>
            <div style="
                font-size:13px;
                margin-top:6px;
                color:#ddd;
            ">
                Trust Score: {score}/100
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# ANSWER CARD
# ==========================================================
def render_answer_box(answer: str):
    st.markdown(
        f"""
        <div style="
            background:#0d0d0d;
            border:1px solid #222;
            padding:18px;
            border-left:4px solid #ff0033;
            margin-bottom:15px;
            line-height:1.7;
            font-size:16px;
        ">
            {answer}
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# EVIDENCE CARDS
# ==========================================================
def render_evidence(evidence: list):

    if not evidence:
        st.info("No strong evidence found.")
        return

    for item in evidence:
        sentence = item.get("sentence", str(item))

        st.markdown(
            f"""
            <div style="
                background:#111;
                border:1px solid #1f1f1f;
                padding:14px;
                margin-bottom:10px;
                border-left:3px solid #ff0033;
                font-size:14px;
                line-height:1.6;
            ">
                {sentence}
            </div>
            """,
            unsafe_allow_html=True
        )


# ==========================================================
# METRIC BOX
# ==========================================================
def render_metric(title: str, value: str):
    st.markdown(
        f"""
        <div style="
            background:#111;
            border:1px solid #222;
            padding:12px;
            text-align:center;
            margin-bottom:10px;
        ">
            <div style="
                font-size:12px;
                color:#999;
                text-transform:uppercase;
                letter-spacing:1px;
            ">
                {title}
            </div>

            <div style="
                font-size:22px;
                font-weight:700;
                color:#fff;
                margin-top:6px;
            ">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )