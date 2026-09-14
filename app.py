import html
import re
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Personal Job Seeker",
    page_icon="💼",
    layout="wide",
)

# ============================================================
# CONSTANTS
# ============================================================

ROLE_ALIASES = {
    "sdet": [
        "sdet",
        "software development engineer in test",
        "software engineer in test",
        "software engineer test",
        "test automation engineer",
        "qa automation engineer",
        "quality engineer",
        "automation test engineer",
    ],
    "software engineer": [
        "software engineer",
        "software development engineer",
        "sde",
        "software developer",
        "backend engineer",
        "frontend engineer",
        "full stack engineer",
        "full-stack engineer",
    ],
}

INDIA_KEYWORDS = [
    "india",
    "indian",
    "bengaluru",
    "bangalore",
    "mumbai",
    "pune",
    "hyderabad",
    "delhi",
    "new delhi",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "indore",
    "remote india",
]

EXPERIENCE_PATTERNS = {
    "Fresher": [
        r"\bfresher\b",
        r"\b0\s*(?:-|to)\s*1\s*years?\b",
        r"\b0\s*years?\b",
        r"\b0-1\b",
        r"\bentry[- ]level\b",
        r"\bgraduate\b",
    ],
    "0-1 years": [
        r"\b0\s*(?:-|to)\s*1\s*years?\b",
        r"\b0-1\b",
        r"\b1\s*year\b",
        r"\bfresher\b",
        r"\bentry[- ]level\b",
    ],
    "1-2 years": [
        r"\b1\s*(?:-|to)\s*2\s*years?\b",
        r"\b1-2\b",
        r"\b2\s*years?\b",
    ],
    "2-3 years": [
        r"\b2\s*(?:-|to)\s*3\s*years?\b",
        r"\b2-3\b",
        r"\b3\s*years?\b",
    ],
    "3-5 years": [
        r"\b3\s*(?:-|to)\s*5\s*years?\b",
        r"\b3-5\b",
        r"\b4\s*years?\b",
        r"\b5\s*years?\b",
    ],
    "5+ years": [
        r"\b5\+?\s*years?\b",
        r"\b6\s*years?\b",
        r"\b7\s*years?\b",
        r"\b8\s*years?\b",
        r"\b9\s*years?\b",
        r"\b10\s*years?\b",
    ],
}

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .subtitle {
            font-size: 17px;
            opacity: 0.75;
            margin-bottom: 30px;
        }

        .job-card {
            border: 1px solid rgba(128,128,128,0.25);
            border-radius: 14px;
            padding: 18px;
            margin: 12px 0;
        }

        .verified {
            font-size: 13px;
            font-weight: 700;
        }

        .warning-box {
            border: 1px solid rgba(255, 165, 0, 0.45);
            border-radius: 10px;
            padding: 14px;
            margin: 10px 0;
        }

        .footer {
            position: fixed;
            bottom: 10px;
            left: 18px;
            font-size: 13px;
            opacity: 0.65;
            z-index: 999;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS
# ============================================================


def clean_text(value):
    """Safely convert any value to clean text."""
    if value is None:
        return ""

    value = str(value).strip()

    # Remove markdown emphasis
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"__(.*?)__", r"\1", value)

    return value.strip()


def normalize_text(value):
    """Normalize text for comparison."""
    value = clean_text(value).lower()

    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9+#.\-\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url):
    """Return a safe normalized HTTP(S) URL or empty string."""
    url = clean_text(url)

    if not url:
        return ""

    # Remove markdown wrappers.
    url = url.strip(" <>[]()")

    # Remove trailing punctuation.
    url = url.rstrip(".,;")

    if not re.match(r"^https?://", url, re.IGNORECASE):
        return ""

    try:
        parsed = urlparse(url)

        if parsed.scheme.lower() not in {"http", "https"}:
            return ""

        if not parsed.netloc:
            return ""

        return url
    except Exception:
        return ""


def extract_url(value):
    """
    Extract a URL from markdown or plain text.

    This function only extracts URLs.
    It does NOT claim that the URL is valid, official,
    or an active application page.
    """
    value = clean_text(value)

    if not value:
        return ""

    markdown_match = re.search(
        r"\[[^\]]*\]\((https?://[^)\s]+)\)",
        value,
        re.IGNORECASE,
    )

    if markdown_match:
        return normalize_url(markdown_match.group(1))

    plain_match = re.search(
        r"https?://[^\s<>\]\)]+",
        value,
        re.IGNORECASE,
    )

    if plain_match:
        return normalize_url(plain_match.group(0))

    return ""


def get_domain(url):
    """Return lowercase hostname."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().split(":")[0]
    except Exception:
        return ""


def company_tokens(company):
    """
    Generate useful company-domain tokens.

    Example:
    'PhonePe' -> ['phonepe']
    'Google India' -> ['google', 'googleindia']
    """
    normalized = normalize_text(company)

    tokens = [
        token
        for token in normalized.split()
        if len(token) >= 3
    ]

    compact = "".join(tokens)

    if compact and compact not in tokens:
        tokens.append(compact)

    return tokens


def looks_like_company_domain(company, url):
    """
    Conservative domain check.

    IMPORTANT:
    This does not prove that a job exists.
    It only checks whether the URL appears related
    to the company name.
    """
    if not company or not url:
        return False

    domain = get_domain(url)

    if not domain:
        return False

    tokens = company_tokens(company)

    for token in tokens:
        if token in domain:
            return True

    return False


def is_probably_career_or_job_url(url):
    """
    Basic URL classification.

    This is deliberately conservative.
    """
    if not url:
        return False

    path = urlparse(url).path.lower()

    indicators = [
        "career",
        "careers",
        "job",
        "jobs",
        "position",
        "positions",
        "opening",
        "openings",
        "apply",
        "requisition",
        "vacancy",
    ]

    return any(indicator in path for indicator in indicators)


def role_matches(requested_role, job_title):
    """
    Deterministic role matching.

    This prevents a requested SDET search from blindly
    accepting every Software Engineer result.
    """
    requested = normalize_text(requested_role)
    title = normalize_text(job_title)

    if not requested or not title:
        return False

    aliases = ROLE_ALIASES.get(requested, [requested])

    for alias in aliases:
        alias_normalized = normalize_text(alias)

        if alias_normalized in title:
            return True

    # Generic fallback.
    requested_words = [
        word
        for word in requested.split()
        if len(word) > 2
    ]

    if not requested_words:
        return False

    matches = sum(word in title for word in requested_words)

    return matches >= max(1, len(requested_words) // 2)


def experience_matches(requested_experience, experience_text):
    """
    Conservative experience matching.
    """
    requested = clean_text(requested_experience)
    text = normalize_text(experience_text)

    if not requested or not text:
        return False

    patterns = EXPERIENCE_PATTERNS.get(requested)

    if not patterns:
        return True

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def location_matches(location):
    """Check whether the job appears to be in India."""
    location = normalize_text(location)

    if not location:
        return False

    return any(keyword in location for keyword in INDIA_KEYWORDS)


def canonical_job_key(job):
    """
    Build deterministic duplicate key.
    Prefer URL because it is usually the strongest identifier.
    """
    url = normalize_url(job.get("direct apply", ""))

    if url:
        parsed = urlparse(url)

        canonical_url = (
            f"{parsed.netloc.lower()}"
            f"{parsed.path.rstrip('/').lower()}"
        )

        return canonical_url

    company = normalize_text(job.get("company", ""))
    title = normalize_text(job.get("role", ""))

    return f"{company}|{title}"


def deduplicate_jobs(rows):
    """Remove duplicate jobs deterministically."""
    unique = {}
    
    for row in rows:
        key = canonical_job_key(row)

        if key and key not in unique:
            unique[key] = row

    return list(unique.values())


def parse_posted_date(value):
    """
    Best-effort date parser.

    Unknown dates go last.
    """
    value = clean_text(value).lower()

    if not value:
        return datetime.min

    now = datetime.now()

    if value in {"today", "just now"}:
        return now

    if value == "yesterday":
        from datetime import timedelta

        return now - timedelta(days=1)

    match = re.search(r"(\d+)\s*(day|days)\s*ago", value)

    if match:
        from datetime import timedelta

        return now - timedelta(days=int(match.group(1)))

    match = re.search(r"(\d+)\s*(hour|hours)\s*ago", value)

    if match:
        from datetime import timedelta

        return now - timedelta(hours=int(match.group(1)))

    # Common date formats.
    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return datetime.min


def validate_job(
    job,
    requested_role,
    requested_experience,
):
    """
    Validate a model-produced job record.

    IMPORTANT:
    This validates structure and consistency.
    It cannot independently prove that a live job exists
    unless the backend has supplied trustworthy source data.
    """

    company = clean_text(job.get("company", ""))
    role = clean_text(job.get("role", ""))
    experience = clean_text(job.get("experience", ""))
    location = clean_text(job.get("location", ""))
    apply_url = extract_url(
        job.get("direct apply")
        or job.get("apply")
        or job.get("apply_url")
        or ""
    )

    if not company or not role:
        return None, "Missing company or role."

    if not role_matches(requested_role, role):
        return None, "Role does not match requested role."

    if requested_experience and experience:
        if not experience_matches(
            requested_experience,
            experience,
        ):
            return None, "Experience does not match requested experience."

    if location:
        if not location_matches(location):
            return None, "Job does not appear to be located in India."

    # Direct Apply is only shown when there is an actual URL.
    if not apply_url:
        job["direct apply"] = ""
    else:
        job["direct apply"] = apply_url

        # Flag suspicious company-domain mismatch.
        if not looks_like_company_domain(company, apply_url):
            job["_url_warning"] = True
        else:
            job["_url_warning"] = False

        job["_career_like_url"] = is_probably_career_or_job_url(
            apply_url
        )

    job["company"] = company
    job["role"] = role
    job["experience"] = experience
    job["location"] = location
    job["posted"] = clean_text(job.get("posted", ""))

    return job, ""


def parse_model_table(text):
    """
    Safely parse a markdown table returned by the model.

    Expected columns:
    Company | Role | Experience | Location | Posted | Direct Apply
    """
    if not text:
        return []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    table_lines = [
        line
        for line in lines
        if line.count("|") >= 2
    ]

    if len(table_lines) < 2:
        return []

    def split_row(line):
        line = line.strip().strip("|")

        return [
            clean_text(cell)
            for cell in line.split("|")
        ]

    header = split_row(table_lines[0])

    # Skip markdown separator row.
    data_start = 1

    if (
        len(table_lines) > 1
        and re.fullmatch(
            r"[\s|:-]+",
            table_lines[1],
        )
    ):
        data_start = 2

    normalized_headers = [
        normalize_text(h)
        for h in header
    ]

    aliases = {
        "company": ["company", "employer"],
        "role": [
            "role",
            "job title",
            "title",
            "position",
        ],
        "experience": [
            "experience",
            "experience required",
            "exp",
        ],
        "location": [
            "location",
            "job location",
            "place",
        ],
        "posted": [
            "posted",
            "posted date",
            "date",
        ],
        "direct apply": [
            "direct apply",
            "apply",
            "apply link",
            "application link",
            "url",
        ],
    }

    field_map = {}

    for canonical, possible_headers in aliases.items():
        for index, header_name in enumerate(normalized_headers):
            if header_name in [
                normalize_text(x)
                for x in possible_headers
            ]:
                field_map[canonical] = index
                break

    # Company + Role are mandatory.
    if "company" not in field_map or "role" not in field_map:
        return []

    rows = []

    for line in table_lines[data_start:]:
        cells = split_row(line)

        if len(cells) < 2:
            continue

        row = {}

        for canonical, index in field_map.items():
            if index < len(cells):
                row[canonical] = cells[index]
            else:
                row[canonical] = ""

        rows.append(row)

    return rows


# ============================================================
# BACKEND
# ============================================================


def search_jobs(role, experience):
    """
    Calls the backend agent.

    IMPORTANT:
    The backend MUST perform real web discovery/grounding.
    This function deliberately does not pretend that Gemini's
    generated text is independently verified.
    """

    try:
        from agent import search_jobs as backend_search

        result = backend_search(
            role=role,
            experience=experience,
        )

        return result

    except Exception as exc:
        st.error(
            "The job-search backend failed. "
            "Check agent.py and your Gemini/API configuration."
        )

        with st.expander("Technical error"):
            st.code(str(exc))

        return ""


# ============================================================
# PDF
# ============================================================


def create_pdf(rows, role, experience):
    """
    Generate a PDF containing only the records currently
    displayed by the application.
    """
    from io import BytesIO

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "Personal Job Seeker",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            f"Role: {html.escape(role)} | "
            f"Experience: {html.escape(experience)}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 8))

    data = [
        [
            "Company",
            "Role",
            "Experience",
            "Location",
            "Apply",
        ]
    ]

    for row in rows:
        company = html.escape(row.get("company", ""))
        job_role = html.escape(row.get("role", ""))
        exp = html.escape(row.get("experience", ""))
        location = html.escape(row.get("location", ""))
        apply_url = row.get("direct apply", "")

        apply_text = (
            f'<link href="{html.escape(apply_url)}">'
            "Apply"
            "</link>"
            if apply_url
            else "Not available"
        )

        data.append(
            [
                Paragraph(company, styles["BodyText"]),
                Paragraph(job_role, styles["BodyText"]),
                Paragraph(exp, styles["BodyText"]),
                Paragraph(location, styles["BodyText"]),
                Paragraph(apply_text, styles["BodyText"]),
            ]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            32 * mm,
            55 * mm,
            30 * mm,
            35 * mm,
            25 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(table)

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Generated by Personal Job Seeker",
            styles["Normal"],
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer


# ============================================================
# UI
# ============================================================

st.markdown(
    '<div class="main-title">💼 Personal Job Seeker</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
        Find relevant opportunities with safer filtering and
        cleaner application links.
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# SEARCH CONTROLS
# ------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    role = st.selectbox(
        "Select role",
        [
            "SDET",
            "Software Engineer",
        ],
    )

with col2:
    experience = st.selectbox(
        "Experience",
        [
            "Fresher",
            "0-1 years",
            "1-2 years",
            "2-3 years",
            "3-5 years",
            "5+ years",
        ],
    )

search_clicked = st.button(
    "🔎 Search Jobs",
    type="primary",
    use_container_width=True,
)

# ------------------------------------------------------------
# SEARC

if search_clicked:
    with st.spinner("Searching for jobs..."):
        raw_result = search_jobs(
            role,
            experience,
        )

    if not raw_result:
        st.warning(
            "No job data was returned by the search backend."
        )
        st.stop()

    rows = parse_model_table(raw_result)

    if not rows:
        st.warning(
            "The search backend returned data, but it could "
            "not be parsed into valid job records."
        )

        with st.expander("Raw backend response"):
            st.code(raw_result)

        st.stop()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    validated_rows = []
    rejected_reasons = []

    for row in rows:
        validated, reason = validate_job(
            row,
            role,
            experience,
        )

        if validated:
            validated_rows.append(validated)
        else:
            rejected_reasons.append(reason)

    # --------------------------------------------------------
    # DEDUPLICATION
    # --------------------------------------------------------

    validated_rows = deduplicate_jobs(
        validated_rows
    )

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    validated_rows.sort(
        key=lambda row: parse_posted_date(
            row.get("posted", "")
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # SESSION STATE
    # --------------------------------------------------------

    st.session_state["jobs"] = validated_rows
    st.session_state["search_role"] = role
    st.session_state["search_experience"] = experience
    st.session_state["rejected"] = rejected_reasons


# ============================================================
# RESULTS
# ============================================================

if "jobs" in st.session_state:

    rows = st.session_state["jobs"]

    search_role = st.session_state.get(
        "search_role",
        role,
    )

    search_experience = st.session_state.get(
        "search_experience",
        experience,
    )

    rejected = st.session_state.get(
        "rejected",
        [],
    )

    st.divider()

    if rows:

        st.subheader(
            f"{len(rows)} matching job"
            f"{'s' if len(rows) != 1 else ''}"
        )

        st.caption(
            "Results are filtered locally for role, experience, "
            "location, duplicate listings, and URL structure. "
            "A URL check alone does not prove that a job is active."
        )

        for index, job in enumerate(rows):

            company = html.escape(
                job.get("company", "")
            )

            job_role = html.escape(
                job.get("role", "")
            )

            exp = html.escape(
                job.get("experience", "")
            )

            location = html.escape(
                job.get("location", "")
            )

            posted = html.escape(
                job.get("posted", "")
            )

            apply_url = job.get(
                "direct apply",
                "",
            )

            st.markdown(
                f"""
                <div class="job-card">
                    <h3>{company}</h3>
                    <strong>{job_role}</strong>
                    <br><br>
                    <b>Experience:</b> {exp or "Not specified"}
                    <br>
                    <b>Location:</b> {location or "Not specified"}
                    <br>
                    <b>Posted:</b> {posted or "Not specified"}
                </div>
                """,
                unsafe_allow_html=True,
            )

            button_col, warning_col = st.columns(
                [1, 3]
            )

            with button_col:

                if apply_url:

                    st.link_button(
                        "Apply Now →",
                        apply_url,
                        use_container_width=True,
                    )

                else:

                    st.button(
                        "Apply unavailable",
                        disabled=True,
                        use_container_width=True,
                        key=f"disabled_{index}",
                    )

            with warning_col:

                if job.get("_url_warning"):

                    st.warning(
                        "The application URL could not be "
                        "confidently matched to the company domain. "
                        "Treat this result as unverified."
                    )

                elif apply_url and not job.get(
                    "_career_like_url",
                    False,
                ):

                    st.warning(
                        "A URL exists, but it does not clearly "
                        "look like a job/application page."
                    )

                elif apply_url:

                    st.markdown(
                        '<div class="verified">✓ URL structure looks valid</div>',
                        unsafe_allow_html=True,
                    )

    else:

        st.warning(
            f"No sufficiently matching {search_role} openings "
            f"were returned for {search_experience}."
        )

        st.info(
            "This is preferable to showing a potentially fake "
            "job listing."
        )

    # --------------------------------------------------------
    # REJECTED RESULTS

if rejected:

        with st.expander(
            f"Why {len(rejected)} result(s) were rejected"
        ):

            for reason in rejected:
                st.write(f"• {reason}")

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

if rows:

    pdf = create_pdf(
            rows,
            search_role,
            search_experience,
        )

    st.download_button(
            label="📄 Download Job Report",
            data=pdf,
            file_name="personal_job_seeker_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        Made with ❤️ by Akash Goswami
    </div>
    """,
    unsafe_allow_html=True,
)
