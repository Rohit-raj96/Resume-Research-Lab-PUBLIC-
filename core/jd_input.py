# core/jd_input.py - PURE FUNCTIONS ONLY (no Streamlit!)
from pathlib import Path
from typing import Optional, Tuple

JD_DIR = Path("jobdescriptions")

def get_jd_options() -> Tuple[Optional[str], Optional[str]]:
    """Returns (file_jd_text, pasted_jd_text) - caller decides priority."""
    file_jd = None
    pasted_jd = None
    
    # File JDs
    if JD_DIR.exists():
        jdfiles = sorted(JD_DIR.glob("*.txt"))
        if jdfiles:
            # Return first available file JD (or handle selection in UI)
            file_jd = jdfiles[0].read_text(encoding="utf-8")
    
    return file_jd, pasted_jd

def create_sample_jd() -> None:
    """Create sample JD file."""
    JD_DIR.mkdir(exist_ok=True)
    sample_jd = JD_DIR / "data_analyst.txt"
    if not sample_jd.exists():
        sample_content = """Data Analyst - Python, SQL, Pandas, Power BI
• 3+ years experience in data analysis
• Advanced Excel, Power Query
• SQL querying, data visualization"""
        sample_jd.write_text(sample_content)
