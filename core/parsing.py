from groq import Groq
from core.config import GROQ_API_KEY, GROQ_MODEL
from core.models import ResumeData
import json
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a professional ATS-style resume parser.
Return ONLY valid JSON that matches the provided schema.
Do not hallucinate; if a field is missing, use empty string or empty list.
"""

def build_parsing_user_prompt(resume_text: str) -> str:
    schema_hint = {
        "name": "string",
        "email": "string",
        "phone": "string",
        "location": "string",
        "current_role": "string",
        "total_experience_years": "float",
        "skills": {
            "programming_languages": ["string"],
            "libraries_frameworks": ["string"],
            "databases": ["string"],
            "tools_platforms": ["string"]
        },
        "education": [
            {
                "degree": "string",
                "branch": "string",
                "institution": "string",
                "start_year": "int or null",
                "end_year": "int or null"
            }
        ],
        "work_experience": [
            {
                "company": "string",
                "designation": "string",
                "start_date": "YYYY-MM or string",
                "end_date": "YYYY-MM or string",
                "is_current": "bool",
                "responsibilities": ["string"]
            }
        ],
        "projects": [
            {
                "title": "string",
                "tech_stack": ["string"],
                "summary": "string"
            }
        ],
        "certifications": ["string"],
        "links": {
            "linkedin": "string",
            "github": "string",
            "portfolio": "string"
        }
    }
    return (
        "Parse the following resume text into the given JSON shape.\n\n"
        f"JSON_SHAPE:\n{schema_hint}\n\n"
        f"RESUME_TEXT:\n{resume_text}"
    )

def parse_resume_text(resume_text: str) -> ResumeData:
    trimmed = resume_text[:8000]
    user_prompt = build_parsing_user_prompt(trimmed)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    raw_json = resp.choices[0].message.content
    return ResumeData.model_validate_json(raw_json)



if __name__ == "__main__":
    print("🔍 Testing Resume Parsing")
    print("=" * 50)
    
    # Test 1: Sample resume text (no PDF needed)
    sample_text = """
    Arshdeep Singh
    Data Analyst | Python | SQL | Power BI
    +91-XXXXXXXXXX | arshdeep@email.com | Delhi
    
    EXPERIENCE
    Data Analyst, ABC Corp (2021-Present)
    • Python, SQL, Power BI dashboards
    • Analyzed 10M+ rows daily
    
    SKILLS
    Python, SQL, Pandas, Tableau, Excel
    """
    
    print("📄 Testing with sample text...")
    try:
        parsed = parse_resume_text(sample_text)
        print("✅ Parsing SUCCESS!")
        print(f"👤 Name: {parsed.name}")
        print(f"📞 Phone: {parsed.phone}")
        print(f"💼 Skills: {len(parsed.skills.programming)} programming skills")
        print("\n📋 Full JSON:")
        print(json.dumps(parsed.model_dump(), indent=2)[:1000] + "...")
    except Exception as e:
        print(f"❌ Parsing error: {e}")
    
    print("\n" + "=" * 50)
