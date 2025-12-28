# core/tailor_full.py
import json
from groq import Groq
from core.config import GROQ_API_KEY, GROQ_MODEL
from core.models import ResumeData, ATSScore

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT_TAILOR_FULL = """
You are a professional resume writer and ATS optimization expert.

INPUTS YOU RECEIVE:
1) RESUME_JSON: the candidate's current, true experience.
2) ATS_SCORE_JSON: scoring of that resume against ONE job description, including
   - missing_critical_skills
   - missing_nice_to_have_skills
   - improvements
3) JOB_DESCRIPTION: the full JD text.

YOUR GOAL:
Create a FULL, TAILORED resume that matches THIS job description as closely as possible WITHOUT LYING.

STRICT TRUTH RULES:
- You must NOT invent fake companies, fake job titles, or fake years of experience.
- You may only:
  - Rephrase existing bullets,
  - Reorder experience,
  - Emphasize certain tasks/skills that the candidate ALREADY has,
  - Add reasonable, small details that are consistent with the existing resume.
- If the JD asks for technologies the candidate clearly has never used (e.g. Java, JIRA, AWS) you may:
  - NOT claim professional experience with them.
  - At most, add a small line like "Learning Java and AWS (self-study)" in SKILLS.

USE THE ATS SCORE:
- Look at missing_critical_skills and missing_nice_to_have_skills.
- Where they are CLOSE to the candidate's existing skills, adjust wording.
  Example: If the candidate has "REST APIs" and the JD wants "OpenAPI", you can say:
    "Designed and documented REST APIs using OpenAPI-like specifications".
- Where they are NOT close at all (e.g. Customer Service, BPMN, BPO for a Python developer), do NOT force them into experience.

HEADLINE RULE:
- The headline MUST be tailored to the JD's target role.
  Example:
  - For a logistics full-stack developer JD → "Full Stack Developer – Logistics SaaS (Python/Backend)".
  - For a developer experience JD → "Senior Developer Experience Engineer (Python SDKs)".
- Never leave a generic "Data Analyst" headline if the JD is for a developer.

OUTPUT FORMAT (PLAIN-TEXT RESUME ONLY):
- No JSON, no markdown, no explanations.
- Do NOT include sections like "What I changed", "Before/After", "Suggestions".
- Output only the final resume text, ready for ATS scanning.

STRUCTURE:

[NAME]
[Target Role Headline]

SUMMARY
- 2–4 bullets focusing on this JD.

SKILLS
- Grouped bullet points.
- Include relevant skills the candidate truly has.
- Optionally one line for "Currently learning: ..." for JD technologies the candidate is studying but not yet using professionally.

EXPERIENCE
[Company] – [Role] – [Dates]
- Bullets rewritten to highlight tasks that match this JD.

PROJECTS
- Only real projects from RESUME_JSON, rewritten to match JD language.

EDUCATION
- Degree, University, Year
"""


def build_tailor_full_prompt(
    resume: ResumeData,
    score: ATSScore,
    jd_text: str
) -> str:
    return (
        "Here is the structured RESUME_JSON:\n"
        f"{resume.model_dump_json(indent=2)}\n\n"
        "Here is the ATS_SCORE_JSON (use missing skills & improvements to guide changes):\n"
        f"{score.model_dump_json(indent=2)}\n\n"
        "Here is the JOB_DESCRIPTION:\n"
        f"{jd_text}\n\n"
        "Now produce the FULL tailored resume text as specified."
    )

def generate_full_tailored_resume(
    resume: ResumeData,
    score: ATSScore,
    jd_text: str
) -> str:
    """Return a full plain-text tailored resume for this JD."""
    prompt = build_tailor_full_prompt(resume, score, jd_text)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "text"},  # plain text
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TAILOR_FULL},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    text = resp.choices[0].message.content
    return text.strip()
# ===== Generic tailoring (no specific JD, only target role) =====

SYSTEM_PROMPT_TAILOR_GENERIC = """
You are a professional resume writer and ATS optimization expert.

INPUTS YOU RECEIVE:
1) RESUME_JSON: the candidate's current, true experience.
2) ATS_SCORE_JSON: generic scoring of that resume (no specific JD).
3) TARGET_ROLE: the main role the candidate is aiming for (e.g. "Data Analyst", "ML Engineer").

YOUR GOAL:
Create a FULL, ATS-friendly resume tailored for the TARGET_ROLE, without any specific job description text.
Optimize for clarity, structure, and keyword coverage for that role, but DO NOT lie.

STRICT TRUTH RULES:
- You must NOT invent fake companies, fake job titles, or fake years of experience.
- You may only:
  - Rephrase existing bullets,
  - Reorder experience,
  - Emphasize tasks/skills the candidate ALREADY has,
  - Add small, reasonable details consistent with the resume.
- If the TARGET_ROLE usually uses technologies the candidate clearly has never used, you may:
  - NOT claim professional experience with them.
  - At most, add a small line like "Currently learning: X, Y" in SKILLS.

OUTPUT FORMAT (PLAIN-TEXT RESUME ONLY):
- No JSON, no markdown, no explanations.
- Output only the final resume text, ready for ATS scanning.

STRUCTURE:

[NAME]
[Target Role Headline for TARGET_ROLE]

SUMMARY
- 2–4 bullets focusing on this target role.

SKILLS
- Grouped bullet points.
- Include relevant skills the candidate truly has.
- Optionally one line: "Currently learning: ..." for technologies they are studying.

EXPERIENCE
[Company] – [Role] – [Dates]
- Bullets rewritten to highlight tasks matching the TARGET_ROLE.

PROJECTS
- Only real projects from RESUME_JSON, rewritten using language relevant to TARGET_ROLE.

EDUCATION
- Degree, University, Year
""".strip()


def build_tailor_generic_prompt(
    resume: ResumeData,
    score: ATSScore,
    target_role: str,
) -> str:
    return (
        "Here is the structured RESUME_JSON:\n"
        f"{resume.model_dump_json(indent=2)}\n\n"
        "Here is the ATS_SCORE_JSON (use weaknesses to guide improvements):\n"
        f"{score.model_dump_json(indent=2)}\n\n"
        f"The TARGET_ROLE is: {target_role}\n\n"
        "Now produce the FULL tailored resume text as specified."
    )


def generate_generic_tailored_resume(
    resume: ResumeData,
    score: ATSScore,
    target_role: str,
) -> str:
    """
    Return a full plain-text tailored resume for a target role, without a specific JD.
    """
    prompt = build_tailor_generic_prompt(resume, score, target_role)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TAILOR_GENERIC},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    text = resp.choices[0].message.content
    return text.strip()
