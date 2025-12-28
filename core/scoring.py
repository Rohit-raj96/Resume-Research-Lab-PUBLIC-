from groq import Groq
from core.config import GROQ_API_KEY, GROQ_MODEL
from core.models import ResumeData, ATSScore
import json

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT_SCORING = """
You are an ATS scoring assistant.
Compare a candidate resume (already parsed as JSON) with a Job Description.
Fill the ATSScore JSON schema.
Scores must be between 0 and 100.
Be conservative. Do not invent experience.
"""

def build_scoring_user_prompt(resume: ResumeData, jd_text: str) -> str:
    schema_hint = {
        "overall_score": "int 0-100",
        "skills_score": "int 0-100",
        "experience_score": "int 0-100",
        "education_score": "int 0-100",
        "domain_match_score": "int 0-100",
        "years_experience_required": "float",
        "years_experience_candidate": "float",
        "matched_skills": ["string"],
        "missing_critical_skills": ["string"],
        "missing_nice_to_have_skills": ["string"],
        "tools_match": ["string"],
        "strengths": ["string"],
        "improvements": ["string"],
        "red_flags": ["string"],
        "resume_section_scores": {
            "summary": "int",
            "skills": "int",
            "projects": "int",
            "experience": "int"
        },
        "is_recommended": "bool",
        "comments": "string"
    }
    return (
        "You are given a parsed resume JSON and a job description text.\n"
        "Evaluate the candidate for this JD and fill the ATSScore JSON.\n\n"
        f"ATSScore_SHAPE:\n{schema_hint}\n\n"
        f"RESUME_JSON:\n{resume.model_dump_json(indent=2)}\n\n"
        f"JOB_DESCRIPTION:\n{jd_text}"
    )

def score_resume_for_jd(resume: ResumeData, jd_text: str) -> ATSScore:
    user_prompt = build_scoring_user_prompt(resume, jd_text)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SCORING},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    raw_json = resp.choices[0].message.content
    return ATSScore.model_validate_json(raw_json)


# NEW: generic ATS scoring (no specific JD)

SYSTEM_PROMPT_GENERIC = """
You are an ATS and resume quality assistant.
Evaluate a candidate resume that is already parsed as JSON.

Your goal is to fill the same ATSScore JSON schema, but:
- Treat "domain_match_score" as overall relevance for generic data / tech jobs.
- "years_experience_required" can be a rough benchmark (e.g. 2, 3, 5).
- Focus on structure, clarity, impact, and keyword richness.

Be conservative. Do not invent experience.
""".strip()


def build_generic_scoring_user_prompt(resume: ResumeData) -> str:
    schema_hint = """
overall_score: int 0-100,
skills_score: int 0-100,
experience_score: int 0-100,
education_score: int 0-100,
domain_match_score: int 0-100,
years_experience_required: float,
years_experience_candidate: float,
matched_skills: string[],
missing_critical_skills: string[],
missing_nice_to_have_skills: string[],
tools_match: string[],
strengths: string[],
improvements: string[],
red_flags: string[],
resume_section_scores: {
  summary: int,
  skills: int,
  projects: int,
  experience: int
},
is_recommended: bool,
comments: string
""".strip()

    return f"""
You are given a parsed resume JSON with no specific job description.
Evaluate the resume for general ATS readiness and data / tech employability.

Fill the ATSScore JSON strictly following this shape:
ATSScore_SHAPE = {{{schema_hint}}}

RESUME_JSON:
{resume.model_dump_json(indent=2)}
""".strip()


def score_resume_generic(resume: ResumeData) -> ATSScore:
    """
    Score a resume for generic ATS readiness (no specific JD).
    """
    user_prompt = build_generic_scoring_user_prompt(resume)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_GENERIC},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    raw_json = resp.choices[0].message.content
    return ATSScore.model_validate_json(raw_json)


if __name__ == "__main__":
    print("🔍 Testing ATS Scoring")
    print("=" * 60)
    
    # Sample parsed resume (from parsing.py output)
    sample_resume = {
        "name": "Arshdeep Singh",
        "skills": {
            "programming": ["Python", "SQL", "Pandas"],
            "tools_platforms": ["Power BI", "Tableau", "Excel"]
        },
        "total_experience_years": 3.5,
        "current_role": "Data Analyst"
    }
    
    # Sample Job Description
    sample_jd = """
    Data Analyst position requiring:
    - Python, SQL, Pandas for data analysis
    - Power BI or Tableau for visualization
    - 3+ years experience
    - Excel advanced
    """
    
    print("📊 Testing scoring...")
    try:
        from core.models import ResumeData, ATSScore
        from core.parsing import parse_resume_text
        
        # Convert dict to ResumeData object
        resume_obj = ResumeData.model_validate(sample_resume)
        
        score = score_resume_for_jd(resume_obj, sample_jd)
        print("✅ Scoring SUCCESS!")
        print(f"🎯 Overall Score: {score.overall_score}%")
        print(f"✅ Matched Skills: {len(score.matched_skills)}")
        print(f"❌ Missing Skills: {len(score.missing_critical_skills)}")
        print("\n📋 Full Score JSON:")
        print(json.dumps(score.model_dump(), indent=2)[:800] + "...")
        
    except Exception as e:
        print(f"❌ Scoring error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
