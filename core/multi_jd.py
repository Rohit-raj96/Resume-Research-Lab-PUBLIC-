# core/multi_jd.py
from pathlib import Path
from typing import List, Tuple
from core.scoring import score_resume_for_jd
from core.models import ResumeData, ATSScore

JD_DIR = Path("job_descriptions")

def load_jd_files() -> List[str]:
    """Return list of JD filenames available in folder."""
    jd_files = sorted(JD_DIR.glob("*.txt"))
    return [f.name for f in jd_files]

def read_jd_file(name: str) -> str:
    """Read a single JD file by name."""
    path = JD_DIR / name
    return path.read_text(encoding="utf-8")

def split_pasted_block(pasted_block: str) -> List[str]:
    """Split pasted multi‑JD text into separate blocks using --- delimiter."""
    parts = []
    current = []
    for line in pasted_block.splitlines():
        if line.strip() == "---":
            if current:
                parts.append("\n".join(current).strip())
                current = []
        else:
            current.append(line)
    if current:
        parts.append("\n".join(current).strip())
    return [p for p in parts if p]

def build_jd_items(selected_files: List[str], pasted_block: str) -> List[Tuple[str, str]]:
    """Return list of (label, jd_text) for selected JDs."""
    jd_items: List[Tuple[str, str]] = []

    # from files
    for name in selected_files:
        try:
            text = read_jd_file(name)
            jd_items.append((f"FILE: {name}", text))
        except Exception:
            continue

    # from pasted text
    if pasted_block.strip():
        parts = split_pasted_block(pasted_block)
        for i, jd_text in enumerate(parts, start=1):
            jd_items.append((f"PASTE JD #{i}", jd_text))

    return jd_items

def score_resume_against_multiple_jds(
    resume: ResumeData,
    jd_items: List[Tuple[str, str]]
) -> List[Tuple[str, ATSScore]]:
    """Core engine: one resume vs many JDs."""
    results: List[Tuple[str, ATSScore]] = []
    for label, jd_text in jd_items:
        score = score_resume_for_jd(resume, jd_text)
        results.append((label, score))
    return results
