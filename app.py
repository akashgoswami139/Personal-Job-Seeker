import importlib
import sys
from io import BytesIO
from unittest.mock import patch

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(page_title="Personal Job Seeker", layout="centered", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .stApp {
            background-color: #F8F9FF;
        }
        .main .block-container {
            max-width: 680px;
            padding-top: 3.5rem;
            padding-bottom: 6rem;
        }
        .app-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: #4C56E0;
            margin-bottom: 0.15rem;
        }
        .app-subtitle {
            font-size: 0.85rem;
            color: #7a7f9a;
            margin-bottom: 2.2rem;
        }
        .field-label {
            font-size: 0.78rem;
            color: #5B6EF5;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.3rem;
            margin-top: 1.2rem;
        }
        .result-header {
            font-size: 0.75rem;
            color: #4A4FD1;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: #EEF1FF;
            padding: 0.5rem 0.6rem;
            margin-top: 2rem;
            border-radius: 6px 6px 0 0;
        }
        .result-row {
            padding: 0.85rem 0.6rem;
            border-bottom: 1px solid #ECEDFB;
            background: #FBFBFF;
            font-size: 0.92rem;
            color: #2b2f45;
        }
        .app-footer {
            position: fixed;
            bottom: 10px;
            left: 16px;
            font-size: 0.75rem;
            color: #9aa0ac;
        }
        .app-footer .heart {
            color: #FF6B81;
        }
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            background-color: #5B6EF5;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.4rem;
            font-weight: 600;
        }
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #4457E8;
            color: #ffffff;
        }
        div[data-testid="stLinkButton"] a {
            background-color: #EEF1FF;
            color: #4A4FD1 !important;
            border: 1px solid #D7DCFF;
            border-radius: 8px;
            padding: 0.35rem 0.9rem;
            font-weight: 600;
            text-decoration: none;
        }
        div[data-testid="stLinkButton"] a:hover {
            background-color: #DFE4FF;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">Personal Job Seeker</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Find verified India jobs directly from company career pages.</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="field-label">Role</div>', unsafe_allow_html=True)
role = st.radio(
    "Role",
    ["SDE", "SDET", "AI Engineer", "ML & DL Engineer"],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown('<div class="field-label">Experience</div>', unsafe_allow_html=True)
experience = st.selectbox(
    "Experience",
    ["Fresher", "0-1 years", "1-2 years", "2-3 years", "3+ years"],
    label_visibility="collapsed",
)

search_clicked = st.button("Search Jobs")


def extract_text(content) -> str:
    """Normalize an LLM response's .content into a plain string.

    Some Gemini responses come back as a list of content parts (strings or
    {"type": "text", "text": ...} dicts) instead of a single string. Handle
    both shapes so downstream parsing always gets a string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
        return "\n".join(parts)
    return str(content)


def get_agent_response(role_value: str, experience_value: str) -> str:
    """Run agent.py's existing objects with the given inputs, without editing that file.

    agent.py collects Role/Experience via input() at module level, so its
    import is deferred until this function runs and its two input() calls
    are fed programmatically for this run. If agent.py exposes a
    search_jobs(role, experience) function, that's used directly; otherwise
    this falls back to invoking its `llm` object on the prompt it already
    built, for compatibility with older versions of agent.py.
    """
    with patch("builtins.input", side_effect=[experience_value, role_value]):
        if "agent" in sys.modules:
            agent_module = importlib.reload(sys.modules["agent"])
        else:
            agent_module = importlib.import_module("agent")

    if hasattr(agent_module, "search_jobs"):
        raw = agent_module.search_jobs(role_value, experience_value)
    else:
        response = agent_module.llm.invoke(agent_module.final_prompt)
        raw = getattr(response, "content", response)

    return extract_text(raw)


def parse_rows(text: str):
    def split_row(line: str):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    candidate_lines = [line for line in text.strip().splitlines() if line.count("|") >= 2]
    if len(candidate_lines) < 2:
        return []

    header = [h.lower() for h in split_row(candidate_lines[0])]
    rows = []
    for line in candidate_lines[1:]:
        cells = split_row(line)
        if all(set(c) <= set("-: ") for c in cells):
            continue  # markdown separator row, e.g. ---|---|---
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def build_pdf(rows, role_value: str, experience_value: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11)
    header_style = ParagraphStyle(
        "header", parent=styles["Normal"], fontSize=9, leading=12,
        textColor=colors.white, fontName="Helvetica-Bold",
    )

    story = [
        Paragraph("Personal Job Seeker - Results", styles["Title"]),
        Paragraph(f"Role: {role_value} &nbsp;|&nbsp; Experience: {experience_value}", styles["Normal"]),
        Spacer(1, 14),
    ]

    table_data = [[Paragraph(h, header_style) for h in ["Company", "Role", "Experience", "Direct Apply"]]]
    for row in rows:
        apply_url = row.get("direct apply") or row.get("apply") or ""
        table_data.append([
            Paragraph(row.get("company", ""), cell_style),
            Paragraph(row.get("role", ""), cell_style),
            Paragraph(row.get("experience", ""), cell_style),
            Paragraph(apply_url, cell_style),
        ])

    table = Table(table_data, colWidths=[150, 100, 90, 170])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5B6EF5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7DCFF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F7FF")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 24))
    story.append(Paragraph("Built by Akash Goswami", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if "results_rows" not in st.session_state:
    st.session_state["results_rows"] = None
    st.session_state["results_role"] = None
    st.session_state["results_experience"] = None

if search_clicked:
    with st.spinner("Searching verified company career pages..."):
        try:
            raw_result = get_agent_response(role, experience)
            st.session_state["results_rows"] = parse_rows(raw_result)
            st.session_state["results_role"] = role
            st.session_state["results_experience"] = experience
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            st.session_state["results_rows"] = None

rows = st.session_state["results_rows"]

if rows is not None:
    if not rows:
        st.info("No verified jobs found for this search.")
    else:
        header_cols = st.columns([3, 2, 2, 2])
        for col, label in zip(header_cols, ["Company", "Role", "Experience", "Direct Apply"]):
            col.markdown(f'<div class="result-header">{label}</div>', unsafe_allow_html=True)

        for i, row in enumerate(rows):
            company = row.get("company", "")
            job_role = row.get("role", "")
            exp = row.get("experience", "")
            apply_url = row.get("direct apply") or row.get("apply") or ""

            cols = st.columns([3, 2, 2, 2])
            cols[0].markdown(f'<div class="result-row">{company}</div>', unsafe_allow_html=True)
            cols[1].markdown(f'<div class="result-row">{job_role}</div>', unsafe_allow_html=True)
            cols[2].markdown(f'<div class="result-row">{exp}</div>', unsafe_allow_html=True)
            with cols[3]:
                if apply_url:
                    st.link_button("Direct Apply", apply_url, key=f"apply_{i}")

        st.write("")
        pdf_bytes = build_pdf(rows, st.session_state["results_role"], st.session_state["results_experience"])
        st.download_button(
            "Download as PDF",
            data=pdf_bytes,
            file_name="personal_job_seeker_results.pdf",
            mime="application/pdf",
        )

st.markdown(
    '<div class="app-footer"><span class="heart">&#10084;&#65039;</span> Built by Akash Goswami '
    '<span class="heart">&#10084;&#65039;</span></div>',
    unsafe_allow_html=True,
)