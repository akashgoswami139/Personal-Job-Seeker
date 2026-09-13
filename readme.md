# Personal Job Seeker Assistant

A minimal AI-powered job search assistant built with **Python, Streamlit, LangChain, and Google Gemini**.

The goal is simple: enter a **job role** and **experience level**, then get relevant job openings in **India** with direct links to the company's official career/application page.

## Features

* 🔎 Search for jobs based on **job role**
* 👨‍💻 Filter by **experience level**
* 🇮🇳 India-only job search
* 🏢 Prioritize official company career pages
* 🚫 No third-party job portals as final application sources
* 🔗 Direct application links
* 🖥️ Minimal Streamlit interface
* 🤖 Google Gemini through LangChain

## Supported Roles

The UI currently provides four role options:

* SDE
* SDET
* AI Engineer
* ML & DL Engineer

## Experience Options

* Fresher
* 0–1 years
* 1–2 years
* 2–3 years
* 3+ years

## Project Structure

```text
Personal-Job-Seeker/
│
├── app.py
├── agent.py
├── .env
├── requirements.txt
└── README.md
```

### `app.py`

The Streamlit frontend.

It handles:

* Role selection
* Experience selection
* Search button
* Displaying job results
* Direct Apply links
* Minimal UI

### `agent.py`

The AI/agent layer.

It handles:

* Prompt construction
* User role and experience input
* Gemini model interaction
* Job-search response generation

The frontend and agent are kept separate so the UI can remain simple.

## AI Model

The project uses Google Gemini through LangChain:

```python
ChatGoogleGenerativeAI
```

The model configured in the current agent is:

```text
gemini-3.5-flash
```

## Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
```

Do not commit your `.env` file to GitHub.

Add this to `.gitignore`:

```text
.env
.env.*
```

## Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd Personal-Job-Seeker
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the Application

Start Streamlit:

```bash
streamlit run app.py
```

The application will open in your browser.

## Usage

1. Select a job role.
2. Select your experience level.
3. Click **Search Jobs**.
4. Review the matching jobs.
5. Use **Direct Apply** to open the application page.

## Result Format

The interface is intentionally minimal and displays only:

```text
Company | Role | Experience | Direct Apply
```

No unnecessary job descriptions, salary information, skills, or other metadata are displayed.

## Job Source Policy

The assistant is designed to prioritize the company's **official careers/jobs website**.

Third-party job platforms such as:

```text
LinkedIn
Naukri
Indeed
Glassdoor
Internshala
```

should not be used as the final application destination.

The preferred result is a direct official company job/application URL.

## Important Note

The quality and availability of current job results depend on the capabilities and configuration of the AI/search layer connected to `agent.py`.

The Streamlit application itself is responsible only for the user interface and displaying the returned results.

## Author

**Akash Goswami**

Built with Python, Streamlit, LangChain, and Gemini.
