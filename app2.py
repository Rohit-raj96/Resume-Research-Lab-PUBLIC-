import streamlit as st
from pathlib import Path

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

st.set_page_config(page_title="Resume Research Lab", layout="wide")
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
                    text = extract_text_from_bytes(st.session_state.uploaded_bytes)
                    parsed = parse_resume_text(text)
                    st.session_state.parsed_resume = parsed
                    st.session_state.ats_score = None
                st.success("Parsed resume.")
            if st.session_state.parsed_resume is not None:
                st.json(st.session_state.parsed_resume.model_dump(), expanded=False)

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
                        score = score_resume_for_jd(
                            st.session_state.parsed_resume,
                            jd_text_single,
                        )
                        st.session_state.ats_score = score
                    st.success("Scoring complete.")

            if st.session_state.ats_score is not None:
                st.json(st.session_state.ats_score.model_dump(), expanded=False)

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
            st.json(parsed.model_dump(), expanded=False)

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
                        results = score_resume_against_multiple_jds(parsed, jd_items)
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
                                tailored = generate_full_tailored_resume(
                                    parsed,
                                    score,
                                    jd_text_for_this,
                                )
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
                    text = extract_text_from_bytes(st.session_state.quick_uploaded_bytes)
                    parsed = parse_resume_text(text)
                    st.session_state.quick_parsed_resume = parsed
                    st.session_state.quick_ats_score = None
                    st.session_state.quick_tailored_resume = ""
                st.success("Parsed resume.")

            if st.session_state.quick_parsed_resume is not None:
                st.json(st.session_state.quick_parsed_resume.model_dump(), expanded=False)

        with col_q2:
            if st.button("Run ATS Quality Check", key="cand_quick_score"):
                if not st.session_state.quick_parsed_resume:
                    st.error("Parse the resume first.")
                else:
                    with st.spinner("Scoring resume for generic ATS readiness..."):
                        score = score_resume_generic(st.session_state.quick_parsed_resume)
                        st.session_state.quick_ats_score = score
                        st.session_state.quick_tailored_resume = ""
                    st.success("Scoring complete.")

            if st.session_state.quick_ats_score is not None:
                st.json(st.session_state.quick_ats_score.model_dump(), expanded=False)

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
                            tailored = generate_generic_tailored_resume(
                                st.session_state.quick_parsed_resume,
                                st.session_state.quick_ats_score,
                                target_role.strip(),
                            )
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
                    text = extract_text_from_bytes(st.session_state.hr_uploaded_bytes)
                    parsed = parse_resume_text(text)
                    st.session_state.hr_parsed_resume = parsed
                    st.session_state.hr_ats_score = None
                st.success("Parsed resume.")
            if st.session_state.hr_parsed_resume is not None:
                st.json(st.session_state.hr_parsed_resume.model_dump(), expanded=False)

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
                        score = score_resume_for_jd(
                            st.session_state.hr_parsed_resume,
                            jd_text_hr,
                        )
                        st.session_state.hr_ats_score = score
                    st.success("Scoring complete.")

            if st.session_state.hr_ats_score is not None:
                st.json(st.session_state.hr_ats_score.model_dump(), expanded=False)

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
                file_bytes_list = [f.read() for f in batch_files]
                filenames = [f.name for f in batch_files]
                ranked_results = process_batch_resumes(
                    file_bytes_list,
                    jd_text_batch,
                    filenames,
                )
                st.session_state.batch_results = ranked_results
                st.success(f"🎉 Ranked {len(ranked_results)} resumes!")

        if st.session_state.batch_results:
            results = st.session_state.batch_results

            st.subheader("🏆 Ranked Results")

            table_data = []
            for i, r in enumerate(results):
                table_data.append(
                    {
                        "Rank": i + 1,
                        "Resume": r["filename"],
                        "Score": f"{r['overall_score']:.1f}%",
                        "Matched Skills": len(r["score"].get("matched_skills", [])),
                        "Missing Critical": len(
                            r["score"].get("missing_critical_skills", [])
                        ),
                    }
                )

            st.dataframe(table_data, use_container_width=True)

            for i, r in enumerate(results):
                with st.expander(f"#{i+1} {r['filename']} ({r['overall_score']:.1f}%)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.json(r["parsed"], expanded=False)
                    with col2:
                        st.json(r["score"], expanded=False)
