import importlib
import re
import sys
from unittest.mock import patch

import streamlit as st

st.set_page_config(page_title="Personal Job Seeker", layout="centered")

st.title("Personal Job Seeker")
st.caption("Find verified India jobs directly from company career pages.")

role = st.radio(
    "Role",
    ["SDE", "SDET", "AI Engineer", "ML & DL Engineer"],
    horizontal=True,
)

experience = st.selectbox(
    "Experience",
    ["Fresher", "0-1 years", "1-2 years", "2-3 years", "3+ years"],
)

search_clicked = st.button("Search Jobs")


def extract_text(content) -> str:
    """Normalize an LLM response's .content into a plain string."""
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
    """Run agent.py's existing objects with the given inputs, without editing that file."""
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


def extract_url(value: str) -> str:
    """Pull a plain URL out of a cell that may be markdown-formatted as [text](url)."""
    if not value:
        return ""
    match = re.search(r"\((https?://[^\s)]+)\)", value)
    if match:
        return match.group(1)
    match = re.search(r"(https?://\S+)", value)
    if match:
        return match.group(1).rstrip(").,")
    return value.strip()


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
        if any("akash goswami" in c.lower() for c in cells):
            continue  # the model's mandatory sign-off line, not a real job row
        rows.append(dict(zip(header, cells)))
    return rows


if "results_rows" not in st.session_state:
    st.session_state["results_rows"] = None

if search_clicked:
    with st.spinner("Searching verified company career pages..."):
        try:
            raw_result = get_agent_response(role, experience)
            st.session_state["results_rows"] = parse_rows(raw_result)
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            st.session_state["results_rows"] = None

rows = st.session_state["results_rows"]

if rows is not None:
    if not rows:
        st.info("No verified jobs found for this search.")
    else:
        header_cols = st.columns([3, 2, 2, 2])
        header_cols[0].write("**Company**")
        header_cols[1].write("**Role**")
        header_cols[2].write("**Experience**")
        header_cols[3].write("**Direct Apply**")

        for i, row in enumerate(rows):
            apply_url = extract_url(row.get("direct apply") or row.get("apply") or "")
            cols = st.columns([3, 2, 2, 2])
            cols[0].write(row.get("company", ""))
            cols[1].write(row.get("role", ""))
            cols[2].write(row.get("experience", ""))
            with cols[3]:
                if apply_url:
                    st.link_button("Apply", apply_url, key=f"apply_{i}")

st.caption("❤️ Built by Akash Goswami ❤️")
