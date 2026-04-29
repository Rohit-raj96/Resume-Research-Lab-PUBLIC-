import html as html_lib
import json
from pathlib import Path

import streamlit as st

# Core engines
from core.pdf_text import extract_text_from_bytes
from core.parsing import parse_resume_text
from core.scoring import score_resume_for_jd
from core.scoring import score_resume_for_jd, score_resume_generic

from core.multi_jd import (
    load_jd_files,
    build_jd_items,
    score_resume_against_multiple_jds,
)
from core.batch_ranking import process_batch_resumes

from core.tailor_full import generate_full_tailored_resume
from core.tailor_full import generate_generic_tailored_resume


JD_DIR = Path("job_descriptions")
SUPPORTED_RESUME_TYPES = ["pdf", "txt", "htm", "html"]


def show_action_error(action: str, exc: Exception) -> None:
    st.error(f"{action} failed: {exc}")


def get_uploaded_file_bytes(uploaded_file) -> bytes:
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()
    return uploaded_file.read()


def inject_intake_styles() -> None:
    st.markdown(
        """
        <style>
        .keka-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin: 0.25rem 0 1rem;
        }
        .keka-skill-chip {
            display: inline-flex;
            align-items: center;
            border: 1px solid #c7d2fe;
            background: #eef2ff;
            color: #26315f;
            border-radius: 6px;
            padding: 0.2rem 0.55rem;
            font-size: 0.84rem;
            line-height: 1.4;
        }
        .keka-parser-note {
            border: 1px dashed #9ca3af;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            color: #4b5563;
            background: #f9fafb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def split_candidate_name(full_name: str):
    parts = [part for part in full_name.split() if part]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def flatten_resume_skills(parsed) -> list[str]:
    skill_groups = parsed.skills.model_dump() if parsed and parsed.skills else {}
    skills = []
    seen = set()
    for values in skill_groups.values():
        for value in values:
            skill = str(value).strip()
            key = skill.lower()
            if skill and key not in seen:
                seen.add(key)
                skills.append(skill)
    return skills


def render_skill_chips(skills: list[str]) -> None:
    if not skills:
        st.caption("No skills detected yet.")
        return

    chips = "".join(
        f'<span class="keka-skill-chip">{html_lib.escape(skill)}</span>'
        for skill in skills
    )
    st.markdown(f'<div class="keka-chip-row">{chips}</div>', unsafe_allow_html=True)


def parse_resume_upload_once(uploaded_file, state_prefix: str):
    if uploaded_file is None:
        return None

    file_bytes = get_uploaded_file_bytes(uploaded_file)
    file_name = uploaded_file.name
    content_type = getattr(uploaded_file, "type", "")

    bytes_key = f"{state_prefix}_uploaded_bytes"
    name_key = f"{state_prefix}_uploaded_name"
    parsed_key = f"{state_prefix}_parsed_resume"
    error_key = f"{state_prefix}_parse_error"

    has_changed = (
        st.session_state.get(bytes_key) != file_bytes
        or st.session_state.get(name_key) != file_name
    )

    if has_changed:
        st.session_state[bytes_key] = file_bytes
        st.session_state[name_key] = file_name
        st.session_state[parsed_key] = None
        st.session_state[error_key] = None

        with st.spinner("Parsing Resume..."):
            try:
                text = extract_text_from_bytes(
                    file_bytes,
                    filename=file_name,
                    content_type=content_type,
                )
                st.session_state[parsed_key] = parse_resume_text(text)
            except Exception as exc:
                st.session_state[error_key] = str(exc)

    st.info(f"Loaded file: {file_name}")
    if st.session_state.get(error_key):
        st.error(
            "Unable to process this file. Please try PDF, TXT, HTM, or HTML, "
            "or enter the details manually below."
        )

    return st.session_state.get(parsed_key)


def render_resume_intake_form(parsed, key_prefix: str) -> dict:
    first_name, middle_name, last_name = split_candidate_name(parsed.name)
    skills = flatten_resume_skills(parsed)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Skills", len(skills))
    metric_cols[1].metric("Experience", f"{parsed.total_experience_years:g} years")
    metric_cols[2].metric("Roles", len(parsed.work_experience))
    metric_cols[3].metric("Education", len(parsed.education))

    st.markdown("### Candidate Details")
    col_a, col_b, col_c = st.columns(3)
    first_name = col_a.text_input("First Name", value=first_name, key=f"{key_prefix}_first")
    middle_name = col_b.text_input("Middle Name", value=middle_name, key=f"{key_prefix}_middle")
    last_name = col_c.text_input("Last Name", value=last_name, key=f"{key_prefix}_last")

    col_d, col_e = st.columns(2)
    email = col_d.text_input("Email", value=parsed.email, key=f"{key_prefix}_email")
    phone = col_e.text_input("Mobile Phone", value=parsed.phone, key=f"{key_prefix}_phone")

    col_f, col_g = st.columns(2)
    location = col_f.text_input(
        "Current Location",
        value=parsed.location,
        key=f"{key_prefix}_location",
    )
    current_role = col_g.text_input(
        "Current Role",
        value=parsed.current_role,
        key=f"{key_prefix}_current_role",
    )

    st.markdown("### Skills")
    render_skill_chips(skills)
    skills_text = st.text_area(
        "Skills",
        value=", ".join(skills),
        height=90,
        key=f"{key_prefix}_skills",
    )
    edited_skills = [
        skill.strip()
        for skill in skills_text.replace("\n", ",").split(",")
        if skill.strip()
    ]

    st.markdown("### Work Experience")
    edited_experience = []
    if not parsed.work_experience:
        st.caption("No work experience detected.")
    for idx, exp in enumerate(parsed.work_experience):
        title = exp.designation or exp.company or f"Experience {idx + 1}"
        with st.expander(title, expanded=idx == 0):
            exp_col_a, exp_col_b = st.columns(2)
            company = exp_col_a.text_input(
                "Company",
                value=exp.company,
                key=f"{key_prefix}_exp_company_{idx}",
            )
            designation = exp_col_b.text_input(
                "Designation",
                value=exp.designation,
                key=f"{key_prefix}_exp_designation_{idx}",
            )
            date_col_a, date_col_b, date_col_c = st.columns([1, 1, 0.8])
            start_date = date_col_a.text_input(
                "Start Date",
                value=exp.start_date,
                key=f"{key_prefix}_exp_start_{idx}",
            )
            end_date = date_col_b.text_input(
                "End Date",
                value=exp.end_date,
                key=f"{key_prefix}_exp_end_{idx}",
            )
            is_current = date_col_c.checkbox(
                "Current",
                value=exp.is_current,
                key=f"{key_prefix}_exp_current_{idx}",
            )
            responsibilities = st.text_area(
                "Responsibilities",
                value="\n".join(exp.responsibilities),
                height=110,
                key=f"{key_prefix}_exp_resp_{idx}",
            )
            edited_experience.append(
                {
                    "company": company,
                    "designation": designation,
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_current": is_current,
                    "responsibilities": [
                        item.strip()
                        for item in responsibilities.splitlines()
                        if item.strip()
                    ],
                }
            )

    st.markdown("### Education")
    edited_education = []
    if not parsed.education:
        st.caption("No education detected.")
    for idx, edu in enumerate(parsed.education):
        title = edu.degree or edu.institution or f"Education {idx + 1}"
        with st.expander(title, expanded=idx == 0):
            edu_col_a, edu_col_b = st.columns(2)
            degree = edu_col_a.text_input(
                "Degree",
                value=edu.degree,
                key=f"{key_prefix}_edu_degree_{idx}",
            )
            branch = edu_col_b.text_input(
                "Branch",
                value=edu.branch,
                key=f"{key_prefix}_edu_branch_{idx}",
            )
            institution = st.text_input(
                "Institution",
                value=edu.institution,
                key=f"{key_prefix}_edu_inst_{idx}",
            )
            year_col_a, year_col_b = st.columns(2)
            start_year = year_col_a.text_input(
                "Start Year",
                value="" if edu.start_year is None else str(edu.start_year),
                key=f"{key_prefix}_edu_start_{idx}",
            )
            end_year = year_col_b.text_input(
                "End Year",
                value="" if edu.end_year is None else str(edu.end_year),
                key=f"{key_prefix}_edu_end_{idx}",
            )
            edited_education.append(
                {
                    "degree": degree,
                    "branch": branch,
                    "institution": institution,
                    "start_year": start_year,
                    "end_year": end_year,
                }
            )

    st.markdown("### Projects")
    edited_projects = []
    if not parsed.projects:
        st.caption("No projects detected.")
    for idx, project in enumerate(parsed.projects):
        title = project.title or f"Project {idx + 1}"
        with st.expander(title, expanded=idx == 0):
            project_title = st.text_input(
                "Project Title",
                value=project.title,
                key=f"{key_prefix}_project_title_{idx}",
            )
            tech_stack = st.text_input(
                "Tech Stack",
                value=", ".join(project.tech_stack),
                key=f"{key_prefix}_project_stack_{idx}",
            )
            summary = st.text_area(
                "Summary",
                value=project.summary,
                height=100,
                key=f"{key_prefix}_project_summary_{idx}",
            )
            edited_projects.append(
                {
                    "title": project_title,
                    "tech_stack": [
                        tech.strip()
                        for tech in tech_stack.split(",")
                        if tech.strip()
                    ],
                    "summary": summary,
                }
            )

    st.markdown("### Links")
    edited_links = {}
    link_cols = st.columns(3)
    for idx, link_name in enumerate(["linkedin", "github", "portfolio"]):
        edited_links[link_name] = link_cols[idx].text_input(
            link_name.title(),
            value=parsed.links.get(link_name, ""),
            key=f"{key_prefix}_link_{link_name}",
        )

    profile_snapshot = {
        "name": " ".join(part for part in [first_name, middle_name, last_name] if part),
        "email": email,
        "phone": phone,
        "location": location,
        "current_role": current_role,
        "total_experience_years": parsed.total_experience_years,
        "skills": edited_skills,
        "work_experience": edited_experience,
        "education": edited_education,
        "projects": edited_projects,
        "certifications": parsed.certifications,
        "links": edited_links,
    }

    st.download_button(
        "Download parsed profile JSON",
        data=json.dumps(profile_snapshot, indent=2),
        file_name="parsed_resume_profile.json",
        mime="application/json",
        key=f"{key_prefix}_download_profile",
    )

    with st.expander("Raw parser JSON", expanded=False):
        st.json(parsed.model_dump(), expanded=False)


    return profile_snapshot


def adapt_batch_results_for_hr(results):
    """
    Converts internal batch ranking output into HR-friendly table rows
    """
    table_rows = []

    for idx, r in enumerate(results, start=1):
        score = r.get("score", {})
        overall = r.get("overall_score", 0)

        # Verdict logic (simple & explainable)
        if overall >= 75:
            verdict = "SHORTLIST"
        elif overall >= 55:
            verdict = "HOLD"
        else:
            verdict = "REJECT"
        
        missing = score.get("missing_critical_skills", [])
        matched = score.get("matched_skills", [])

        if overall >= 75:
            explanation = "Meets most required skills with strong alignment."
        elif overall >= 55:
            explanation = (
                "Some skill gaps detected: "
                + ", ".join(missing[:3])
                if missing
                else "Moderate match with minor gaps."
            )
        else:
            explanation = (
                "Major skill gaps: "
                + ", ".join(missing[:3])
                if missing
                else "Low overall match."
            )


        table_rows.append(
            {
                "Rank": idx,
                "Candidate": r.get("filename", "N/A"),
                "Verdict": verdict,
                "Match %": f"{overall:.1f}%",
                "Skills Fit": "Strong" if overall >= 75 else "Partial" if overall >= 55 else "Weak",
                "Missing Critical Skills": len(score.get("missing_critical_skills", [])),
                "Explanation": explanation,
            }
        )

    return table_rows
def render_parsed_resume_table(parsed) -> None:
    import pandas as pd
    data = parsed.model_dump()

    st.markdown("#### 👤 Candidate Info")
    basic = {
        "Name": data.get("name", ""),
        "Email": data.get("email", ""),
        "Phone": data.get("phone", ""),
        "Location": data.get("location", ""),
        "Current Role": data.get("current_role", ""),
        "Experience (yrs)": data.get("total_experience_years", ""),
    }
    import pandas as pd
    st.table(pd.DataFrame(basic.items(), columns=["Field", "Value"]))

    skills_raw = data.get("skills", {})
    all_skills = []
    for group, vals in skills_raw.items():
        for v in vals:
            all_skills.append({"Category": group.replace("_", " ").title(), "Skill": v})
    if all_skills:
        st.markdown("#### 🛠️ Skills")
        st.dataframe(pd.DataFrame(all_skills), use_container_width=True, hide_index=True)

    work = data.get("work_experience", [])
    if work:
        st.markdown("#### 💼 Work Experience")
        st.dataframe(pd.DataFrame([{
            "Company": w.get("company", ""),
            "Designation": w.get("designation", ""),
            "Start": w.get("start_date", ""),
            "End": w.get("end_date", ""),
            "Current": "✅" if w.get("is_current") else "",
        } for w in work]), use_container_width=True, hide_index=True)

    edu = data.get("education", [])
    if edu:
        st.markdown("#### 🎓 Education")
        st.dataframe(pd.DataFrame([{
            "Degree": e.get("degree", ""),
            "Branch": e.get("branch", ""),
            "Institution": e.get("institution", ""),
            "Year": e.get("end_year", ""),
        } for e in edu]), use_container_width=True, hide_index=True)

    projects = data.get("projects", [])
    if projects:
        st.markdown("#### 🚀 Projects")
        st.dataframe(pd.DataFrame([{
            "Title": p.get("title", ""),
            "Tech Stack": ", ".join(p.get("tech_stack", [])),
            "Summary": p.get("summary", "")[:100] + "..." if len(p.get("summary", "")) > 100 else p.get("summary", ""),
        } for p in projects]), use_container_width=True, hide_index=True)

    with st.expander("🔧 Raw JSON (for debugging)", expanded=False):
        st.json(data, expanded=False)


def render_ats_score_table(score) -> None:
    import pandas as pd
    data = score.model_dump()

    st.markdown("#### 📊 ATS Score Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall", f"{data['overall_score']}%")
    c2.metric("Skills", f"{data['skills_score']}%")
    c3.metric("Experience", f"{data['experience_score']}%")
    c4.metric("Education", f"{data['education_score']}%")
    c5.metric("Domain", f"{data['domain_match_score']}%")

    verdict = data.get("is_recommended", False)
    if verdict:
        st.success("✅ Recommended — This resume is a strong match.")
    else:
        st.warning("⚠️ Not Recommended — Gaps found. See details below.")

    st.caption(f"💬 {data.get('comments', '')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**✅ Matched Skills**")
        matched = data.get("matched_skills", [])
        if matched:
            st.dataframe(pd.DataFrame(matched, columns=["Skill"]), use_container_width=True, hide_index=True)
        else:
            st.caption("None detected.")

        st.markdown("**💪 Strengths**")
        for s in data.get("strengths", []):
            st.write(f"- {s}")

    with col_b:
        st.markdown("**❌ Missing Critical Skills**")
        missing = data.get("missing_critical_skills", [])
        if missing:
            st.dataframe(pd.DataFrame(missing, columns=["Skill"]), use_container_width=True, hide_index=True)
        else:
            st.caption("None — great match!")

        st.markdown("**🔧 Improvements**")
        for imp in data.get("improvements", []):
            st.write(f"- {imp}")

    red_flags = data.get("red_flags", [])
    if red_flags:
        st.markdown("**🚩 Red Flags**")
        for r in red_flags:
            st.error(f"- {r}")

    section_scores = data.get("resume_section_scores", {})
    if section_scores:
        st.markdown("#### 📋 Section-wise Scores")
        st.dataframe(
            pd.DataFrame(section_scores.items(), columns=["Section", "Score"]),
            use_container_width=True, hide_index=True
        )

    with st.expander("🔧 Raw JSON (for debugging)", expanded=False):
        st.json(data, expanded=False)

st.set_page_config(page_title="Resume Research Lab", layout="wide")
inject_intake_styles()
st.title("Resume Processing Research Lab")

# ---------- Top-level role tabs ----------
candidate_tab, hr_tab = st.tabs(["👤 Candidate Corner", "🏢 HR Corner"])

# Ensure session keys exist
if "uploaded_bytes" not in st.session_state:
    st.session_state.uploaded_bytes = None
if "parsed_resume" not in st.session_state:
    st.session_state.parsed_resume = None
if "ats_score" not in st.session_state:
    st.session_state.ats_score = None
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
if "multi_jd_results" not in st.session_state:
    st.session_state.multi_jd_results = None
if "tailored_resumes" not in st.session_state:
    st.session_state.tailored_resumes = {}


# =========================================================
# =============   CANDIDATE  CORNER   =====================
# =========================================================
with candidate_tab:
    c1, c2, c3 = st.tabs(
        [
            "📄 Single JD match",
            "🔁 Multi‑JD comparison",
            "⭐ (optional) future Quick ATS",
        ]
    )

    # -----------------------------------------------------
    # C1: Single resume vs ONE JD  (was old tab2)
    # -----------------------------------------------------
    with c1:
        st.header("Single Resume vs One Job Description")

        uploaded_file = st.file_uploader(
            "Upload your resume (PDF or TXT)",
            type=["pdf", "txt"],
            key="cand_single_upload",
        )

        # Detect new file and reset state
        if uploaded_file is not None:
            new_bytes = uploaded_file.read()
            if new_bytes != st.session_state.uploaded_bytes:
                st.session_state.uploaded_bytes = new_bytes
                st.session_state.parsed_resume = None
                st.session_state.ats_score = None
            st.info(f"Loaded file: {uploaded_file.name}")

        col_left, col_right = st.columns(2)

        # LEFT: parsing
        with col_left:
            if st.button("Run Parsing", key="cand_single_parse") and st.session_state.uploaded_bytes:
                with st.spinner("Parsing resume..."):
                    try:
                        text = extract_text_from_bytes(st.session_state.uploaded_bytes)
                        parsed = parse_resume_text(text)
                    except Exception as exc:
                        show_action_error("Parsing", exc)
                    else:
                        st.session_state.parsed_resume = parsed
                        st.session_state.ats_score = None
                        st.success("Parsed resume.")
            if st.session_state.parsed_resume is not None:
                # st.json(st.session_state.parsed_resume.model_dump(), expanded=False)
                render_parsed_resume_table(st.session_state.parsed_resume)
        # RIGHT: JD + scoring
        with col_right:
            st.markdown("### Job Description")

            # JD file select
            jd_files = sorted(JD_DIR.glob("*.txt"))
            jd_names = [f.name for f in jd_files]
            selected_jdname = st.selectbox(
                "Select JD file",
                jd_names if jd_files else ["None"],
                key="cand_single_jd_file",
            )

            jd_text_single = ""
            if jd_files and selected_jdname != "None":
                jd_path = JD_DIR / selected_jdname
                jd_text_single = jd_path.read_text(encoding="utf-8")

            pasted_jd_single = st.text_area(
                "Or paste JD here",
                height=120,
                placeholder="Paste job description...",
                key="cand_single_jd_paste",
            )
            if pasted_jd_single.strip():
                jd_text_single = pasted_jd_single

            if st.button("Run ATS Scoring", key="cand_single_score"):
                if not st.session_state.parsed_resume:
                    st.error("Parse the resume first.")
                elif not jd_text_single:
                    st.error("Select or paste a Job Description first.")
                else:
                    with st.spinner("Scoring resume against JD..."):
                        try:
                            score = score_resume_for_jd(
                                st.session_state.parsed_resume,
                                jd_text_single,
                            )
                        except Exception as exc:
                            show_action_error("ATS scoring", exc)
                        else:
                            st.session_state.ats_score = score
                            st.success("Scoring complete.")

            if st.session_state.ats_score is not None:
                # st.json(st.session_state.ats_score.model_dump(), expanded=False)
                render_ats_score_table(st.session_state.ats_score)


    # -----------------------------------------------------
    # C2: One resume vs MULTIPLE JDs  (was old tab3)
    # -----------------------------------------------------
    with c2:
        st.header("One Resume vs Multiple Job Descriptions")

        if st.session_state.parsed_resume is None:
            st.warning("First go to '📄 Single JD match' and parse your resume.")
        else:
            parsed = st.session_state.parsed_resume

            st.subheader("👤 Candidate Snapshot")
            # st.json(parsed.model_dump(), expanded=False)
            render_parsed_resume_table(parsed)

            st.markdown("---")
            st.subheader("📋 Select / Paste Job Descriptions")

            col_left, col_right = st.columns(2)

            # LEFT: multi-select JD files
            with col_left:
                jd_names_multi = load_jd_files()
                selected_jd_files = st.multiselect(
                    "Select one or more JD files",
                    jd_names_multi,
                    help="Each selected file will be scored separately.",
                    key="cand_multi_jd_files",
                )

            # RIGHT: pasted multi-JD block
            with col_right:
                pasted_block = st.text_area(
                    "Or paste multiple JDs (separate with a line containing only ---)",
                    height=220,
                    placeholder=(
                        "JD: Data Analyst - Banking...\n"
                        "---\n"
                        "JD: Data Analyst - E-commerce...\n"
                        "---\n"
                        "JD: Data Analyst - Healthcare..."
                    ),
                    key="cand_multi_jd_paste",
                )

            jd_items = build_jd_items(selected_jd_files, pasted_block)
            jd_text_map = {label: jd_text for (label, jd_text) in jd_items}

            st.markdown("---")

            if st.button(
                "🚀 Score Against All Selected JDs",
                type="primary",
                key="cand_multi_score_all",
            ):
                if not jd_items:
                    st.error("Select at least one JD file or paste at least one JD block.")
                else:
                    with st.spinner("Scoring resume against multiple JDs..."):
                        try:
                            results = score_resume_against_multiple_jds(parsed, jd_items)
                        except Exception as exc:
                            show_action_error("Multi-JD scoring", exc)
                        else:
                            st.session_state.multi_jd_results = results
                            st.success(f"Scored against {len(results)} job descriptions.")

            if st.session_state.multi_jd_results:
                results = st.session_state.multi_jd_results

                st.subheader("📊 Scores per Job Description")
                table_rows = []
                for label, score in results:
                    table_rows.append(
                        {
                            "JD": label,
                            "Overall %": score.overall_score,
                            "Skills %": score.skills_score,
                            "Experience %": score.experience_score,
                            "Missing critical": len(score.missing_critical_skills),
                            "Recommended?": "✅" if score.is_recommended else "❌",
                        }
                    )
                st.dataframe(table_rows, use_container_width=True)

                st.subheader("🔍 Per‑JD Details, Recommendations & Tailored Resume")
                for label, score in results:
                    with st.expander(f"{label} – {score.overall_score}% match"):
                        col_a, col_b = st.columns(2)

                        with col_a:
                            st.markdown("**Missing critical skills**")
                            if score.missing_critical_skills:
                                for s in score.missing_critical_skills:
                                    st.write(f"- {s}")
                            else:
                                st.write("None.")

                            st.markdown("**Missing nice‑to‑have skills**")
                            if score.missing_nice_to_have_skills:
                                for s in score.missing_nice_to_have_skills:
                                    st.write(f"- {s}")
                            else:
                                st.write("None.")

                        with col_b:
                            st.markdown("**Suggested resume improvements**")
                            if score.improvements:
                                for imp in score.improvements[:5]:
                                    st.write(f"- {imp}")
                            else:
                                st.write("No major issues detected.")

                            st.markdown("**Strengths**")
                            if score.strengths:
                                for s in score.strengths[:5]:
                                    st.write(f"- {s}")
                            else:
                                st.write("Not specified.")

                        st.markdown("---")

                        jd_text_for_this = jd_text_map.get(label, "")

                        if score.overall_score < 40:
                            st.warning(
                                "This JD has a very low match score "
                                f"({score.overall_score}%). Tailoring may not be useful and "
                                "will not invent experience you don't have."
                            )

                        tailor_key = f"tailor_{label}"
                        if st.button(
                            f"✏️ Generate tailored resume for {label}",
                            key=tailor_key,
                        ):
                            with st.spinner("Generating full tailored resume..."):
                                try:
                                    tailored = generate_full_tailored_resume(
                                        parsed,
                                        score,
                                        jd_text_for_this,
                                    )
                                except Exception as exc:
                                    show_action_error("Tailored resume generation", exc)
                                else:
                                    st.session_state.tailored_resumes[label] = tailored
                                    st.success(
                                        "Tailored resume generated. You can edit before downloading."
                                    )

                        if label in st.session_state.tailored_resumes:
                            edited = st.text_area(
                                "Tailored resume (edit before download)",
                                value=st.session_state.tailored_resumes[label],
                                height=400,
                                key=f"edit_{label}",
                            )

                            st.download_button(
                                "⬇️ Download tailored resume",
                                data=edited,
                                file_name=f"tailored_{label.replace(' ', '_')}.txt",
                                mime="text/plain",
                                key=f"download_{label}",
                            )

    # -----------------------------------------------------
    # C3: Quick ATS score (no JD)
    with c3:
        st.header("Quick ATS score (no specific JD)")

        quick_upload = st.file_uploader(
            "Upload your resume (PDF or TXT)",
            type=["pdf", "txt"],
            key="cand_quick_upload",
        )

        if "quick_uploaded_bytes" not in st.session_state:
            st.session_state.quick_uploaded_bytes = None
        if "quick_parsed_resume" not in st.session_state:
            st.session_state.quick_parsed_resume = None
        if "quick_ats_score" not in st.session_state:
            st.session_state.quick_ats_score = None
        if "quick_tailored_resume" not in st.session_state:
            st.session_state.quick_tailored_resume = ""

        if quick_upload is not None:
            new_bytes = quick_upload.read()
            if new_bytes != st.session_state.quick_uploaded_bytes:
                st.session_state.quick_uploaded_bytes = new_bytes
                st.session_state.quick_parsed_resume = None
                st.session_state.quick_ats_score = None
                st.session_state.quick_tailored_resume = ""
            st.info(f"Loaded file: {quick_upload.name}")

        col_q1, col_q2 = st.columns(2)

        with col_q1:
            if st.button("Run Parsing", key="cand_quick_parse") and st.session_state.quick_uploaded_bytes:
                with st.spinner("Parsing resume..."):
                    try:
                        text = extract_text_from_bytes(st.session_state.quick_uploaded_bytes)
                        parsed = parse_resume_text(text)
                    except Exception as exc:
                        show_action_error("Parsing", exc)
                    else:
                        st.session_state.quick_parsed_resume = parsed
                        st.session_state.quick_ats_score = None
                        st.session_state.quick_tailored_resume = ""
                        st.success("Parsed resume.")

            if st.session_state.quick_parsed_resume is not None:
                # st.json(st.session_state.quick_parsed_resume.model_dump(), expanded=False)
                render_parsed_resume_table(st.session_state.quick_parsed_resume)

        with col_q2:
            if st.button("Run ATS Quality Check", key="cand_quick_score"):
                if not st.session_state.quick_parsed_resume:
                    st.error("Parse the resume first.")
                else:
                    with st.spinner("Scoring resume for generic ATS readiness..."):
                        try:
                            score = score_resume_generic(st.session_state.quick_parsed_resume)
                        except Exception as exc:
                            show_action_error("ATS quality check", exc)
                        else:
                            st.session_state.quick_ats_score = score
                            st.session_state.quick_tailored_resume = ""
                            st.success("Scoring complete.")

            if st.session_state.quick_ats_score is not None:
                # st.json(st.session_state.quick_ats_score.model_dump(), expanded=False)
                render_ats_score_table(st.session_state.quick_ats_score)


                st.markdown("---")
                st.subheader("✏️ Tailored ATS‑friendly resume (no specific JD)")

                target_role = st.text_input(
                    "Target role (e.g. Data Analyst, ML Engineer)",
                    key="cand_quick_target_role",
                )

                if st.button("Generate tailored resume", key="cand_quick_tailor"):
                    if not target_role.strip():
                        st.error("Please enter a target role first.")
                    else:
                        with st.spinner("Generating tailored resume..."):
                            try:
                                tailored = generate_generic_tailored_resume(
                                    st.session_state.quick_parsed_resume,
                                    st.session_state.quick_ats_score,
                                    target_role.strip(),
                                )
                            except Exception as exc:
                                show_action_error("Tailored resume generation", exc)
                            else:
                                st.session_state.quick_tailored_resume = tailored
                                st.success("Tailored resume generated. You can edit below before download.")

                if st.session_state.quick_tailored_resume:
                    edited = st.text_area(
                        "Tailored resume (edit before download)",
                        value=st.session_state.quick_tailored_resume,
                        height=400,
                        key="cand_quick_tailored_text",
                    )

                    st.download_button(
                        "⬇️ Download tailored resume (.txt)",
                        data=edited,
                        file_name="tailored_resume_generic.txt",
                        mime="text/plain",
                        key="cand_quick_download_txt",
                    )


# =========================================================
# ==================   HR  CORNER   =======================
# =========================================================
with hr_tab:
    h1, h2 = st.tabs(
        [
            "🔍 Single candidate check",
            "🚀 Batch Resume Ranking",
        ]
    )

    # -----------------------------------------------------
    # H1: Single candidate vs one JD (HR wording)
    # -----------------------------------------------------
    with h1:
        st.header("Single Candidate vs Job Description")

        hr_upload = st.file_uploader(
            "Upload candidate resume (PDF or TXT)",
            type=["pdf", "txt"],
            key="hr_single_upload",
        )

        if "hr_uploaded_bytes" not in st.session_state:
            st.session_state.hr_uploaded_bytes = None
        if "hr_parsed_resume" not in st.session_state:
            st.session_state.hr_parsed_resume = None
        if "hr_ats_score" not in st.session_state:
            st.session_state.hr_ats_score = None

        if hr_upload is not None:
            new_bytes = hr_upload.read()
            if new_bytes != st.session_state.hr_uploaded_bytes:
                st.session_state.hr_uploaded_bytes = new_bytes
                st.session_state.hr_parsed_resume = None
                st.session_state.hr_ats_score = None
            st.info(f"Loaded file: {hr_upload.name}")

        col_l, col_r = st.columns(2)

        with col_l:
            if st.button("Run Parsing", key="hr_single_parse") and st.session_state.hr_uploaded_bytes:
                with st.spinner("Parsing resume..."):
                    try:
                        text = extract_text_from_bytes(st.session_state.hr_uploaded_bytes)
                        parsed = parse_resume_text(text)
                    except Exception as exc:
                        show_action_error("Parsing", exc)
                    else:
                        st.session_state.hr_parsed_resume = parsed
                        st.session_state.hr_ats_score = None
                        st.success("Parsed resume.")
            if st.session_state.hr_parsed_resume is not None:
                # st.json(st.session_state.hr_parsed_resume.model_dump(), expanded=False)
                render_parsed_resume_table(st.session_state.hr_parsed_resume)

        with col_r:
            st.markdown("### Target Job Description")

            jd_files_hr = sorted(JD_DIR.glob("*.txt"))
            jd_names_hr = [f.name for f in jd_files_hr]
            selected_jd_hr = st.selectbox(
                "Select JD file",
                jd_names_hr if jd_files_hr else ["None"],
                key="hr_single_jd_file",
            )

            jd_text_hr = ""
            if jd_files_hr and selected_jd_hr != "None":
                jd_path = JD_DIR / selected_jd_hr
                jd_text_hr = jd_path.read_text(encoding="utf-8")

            pasted_jd_hr = st.text_area(
                "Or paste JD here",
                height=120,
                placeholder="Paste job description...",
                key="hr_single_jd_paste",
            )
            if pasted_jd_hr.strip():
                jd_text_hr = pasted_jd_hr

            if st.button("Run ATS Scoring", key="hr_single_score"):
                if not st.session_state.hr_parsed_resume:
                    st.error("Parse the resume first.")
                elif not jd_text_hr:
                    st.error("Select or paste a Job Description first.")
                else:
                    with st.spinner("Scoring resume against JD..."):
                        try:
                            score = score_resume_for_jd(
                                st.session_state.hr_parsed_resume,
                                jd_text_hr,
                            )
                        except Exception as exc:
                            show_action_error("ATS scoring", exc)
                        else:
                            st.session_state.hr_ats_score = score
                            st.success("Scoring complete.")

            if st.session_state.hr_ats_score is not None:
                # st.json(st.session_state.hr_ats_score.model_dump(), expanded=False)
                render_ats_score_table(st.session_state.hr_ats_score)

    # -----------------------------------------------------
    # H2: Batch resume ranking (was old tab1)
    # -----------------------------------------------------
    with h2:
        st.header("Batch Resume Ranking")

        # JD for batch
        st.markdown("### Target Job Description for this batch")

        jd_files_batch = sorted(JD_DIR.glob("*.txt"))
        jd_names_batch = [f.name for f in jd_files_batch]
        selected_jd_batch = st.selectbox(
            "Select JD file",
            jd_names_batch if jd_files_batch else ["None"],
            key="hr_batch_jd_file",
        )

        jd_text_batch = ""
        if jd_files_batch and selected_jd_batch != "None":
            jd_path = JD_DIR / selected_jd_batch
            jd_text_batch = jd_path.read_text(encoding="utf-8")

        pasted_jd_batch = st.text_area(
            "Or paste JD here",
            height=120,
            placeholder="Paste job description for this batch...",
            key="hr_batch_jd_paste",
        )
        if pasted_jd_batch.strip():
            jd_text_batch = pasted_jd_batch

        batch_files = st.file_uploader(
            "Upload multiple candidate resumes (PDF)",
            type="pdf",
            accept_multiple_files=True,
            key="hr_batch_upload",
        )

        if batch_files and jd_text_batch:
            if st.button("🚀 RANK ALL", type="primary", key="hr_batch_rank_all"):
                try:
                    file_bytes_list = [f.read() for f in batch_files]
                    filenames = [f.name for f in batch_files]
                    ranked_results = process_batch_resumes(
                        file_bytes_list,
                        jd_text_batch,
                        filenames,
                    )
                except Exception as exc:
                    show_action_error("Batch ranking", exc)
                else:
                    st.session_state.batch_results = ranked_results
                    st.success(f"🎉 Ranked {len(ranked_results)} resumes!")

        if st.session_state.batch_results:
            results = st.session_state.batch_results

            st.subheader("🏆 Ranked Results")

        if st.session_state.batch_results:
            results = st.session_state.batch_results

            st.subheader("🏆 Candidate Evaluation Summary")

            table_data = adapt_batch_results_for_hr(results)

            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
            )
        
