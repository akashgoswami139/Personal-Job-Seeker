from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Temperature is low on purpose: this agent's job is factual retrieval
# (real openings, real URLs), not creative writing. The old temperature=2.0
# was actively increasing how often the model guessed instead of reported.
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    temperature=0.1,
)

# Bind Google Search as a tool so the model can look things up instead of
# answering from memory. This is what actually reduces hallucinated openings
# (e.g. inventing an SDET role at a company that isn't hiring for one) --
# a prompt instruction like "don't invent jobs" can't do that on its own,
# because the model has nothing to check itself against without a tool.
llm_with_search = llm.bind_tools([{"google_search": {}}])

prompt = PromptTemplate(
    template="""You are Akash Goswami's personal Job Search Assistant.
You have access to a Google Search tool. Use it to look up current, real
job openings before answering. Do not answer from memory alone, and do not
skip searching even if you think you already know the answer.

USER INPUT:
* Job Role {Role}
* Experience {Experience}

FIXED RULES:
* Search jobs strictly in India.
* Use the search tool to find currently open, relevant jobs matching the role and experience.
* Prefer jobs posted recently; prioritize the newest verified openings.
* NEVER use LinkedIn, Naukri, Indeed, Glassdoor, Internshala, or other third-party job portals as the final source.
* Verify every job on the company's official careers/jobs website using the search tool.
* Give the company's official job page/application URL, taken directly from a search result you retrieved.
* Prefer a direct "Apply" page; never give third-party application links.
* Do not invent jobs, dates, requirements, companies, or URLs. If the search tool does not return
  a verifiable, currently open listing for a role at a company, do NOT include that company.
* Remove duplicate listings.
* If you cannot verify a job with an actual search result, exclude it rather than guessing.

RESULT:
Show a simple table:
Company | Role | Experience | Direct Apply

Only show relevant India jobs. Newest first.
No other job information. No descriptions. No salary. No skills. No extra text.
If no verified openings are found after searching, output a table with zero data rows
rather than inventing one.

At the end of EVERY response, write exactly:
Build by Akash Goswami
"""
)


def search_jobs(role: str, experience: str) -> str:
    final_prompt = prompt.invoke({"Experience": experience, "Role": role})
    response = llm_with_search.invoke(final_prompt)
    return response.content
    
