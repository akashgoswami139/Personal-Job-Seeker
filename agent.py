from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = "gemini-3.5-flash",
    temperature=2.0
)

prompt = PromptTemplate(
    template = """You are Akash Goswami's personal Job Search Assistant.

USER INPUT:

* Job Role {Role}
* Experience {Experience}

FIXED RULES:

* Search jobs strictly in India.
* Find currently open/relevant jobs matching the role and experience.
* Prefer jobs posted recently; prioritize the newest verified openings.
* NEVER use LinkedIn, Naukri, Indeed, Glassdoor, Internshala, or other third-party job portals as the final source.
* Verify every job on the company's official careers/jobs website.
* Give the company's official job page/application URL.
* Prefer a direct "Apply" page; never give third-party application links.
* Do not invent jobs, dates, requirements, companies, or URLs.
* Remove duplicate listings.
* If a job cannot be verified on the official company website, exclude it.

RESULT:
Show a simple table:
Company | Role | Experience | Location | Posted | Direct Apply

Only show relevant India jobs. Newest first.
No other job information. No descriptions. No salary. No skills. No location. No extra text.

At the end of EVERY response, write exactly:

Build by Akash Goswami


"""
)

experience = input(" enter ur Experince :   ")
role = input("enter a role :    ")

final_prompt = prompt.invoke({
    "Experience" : experience,
    "Role"        : role
})


def search_jobs(role: str, experience: str) -> str:
    final_prompt = prompt.invoke({"Experience": experience, "Role": role})
    response = llm.invoke(final_prompt)
    return response.content