from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class EducationEntry(BaseModel):
    degree: str = ""
    branch: str = ""
    institution: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class WorkExperienceEntry(BaseModel):
    company: str = ""
    designation: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    responsibilities: List[str] = Field(default_factory=list)

class ProjectEntry(BaseModel):
    title: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    summary: str = ""

class Skills(BaseModel):
    programming_languages: List[str] = Field(default_factory=list)
    libraries_frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    tools_platforms: List[str] = Field(default_factory=list)

class ResumeData(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    current_role: str = ""
    total_experience_years: float = 0.0
    skills: Skills = Field(default_factory=Skills)
    education: List[EducationEntry] = Field(default_factory=list)
    work_experience: List[WorkExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    links: Dict[str, str] = Field(default_factory=dict)

class ATSScore(BaseModel):
    overall_score: int
    skills_score: int
    experience_score: int
    education_score: int
    domain_match_score: int
    years_experience_required: float
    years_experience_candidate: float
    matched_skills: List[str]
    missing_critical_skills: List[str]
    missing_nice_to_have_skills: List[str]
    tools_match: List[str]
    strengths: List[str]
    improvements: List[str]
    red_flags: List[str]
    resume_section_scores: Dict[str, int]
    is_recommended: bool
    comments: str
