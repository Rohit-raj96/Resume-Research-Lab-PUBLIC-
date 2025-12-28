"""
Batch Resume Ranking Engine
Handles multiple PDFs → Parse → Score → Rank
Zero dependencies on Streamlit
"""

from typing import List, Dict, Any
from pathlib import Path
import json

from core.pdf_text import extract_text_from_bytes
from core.parsing import parse_resume_text
from core.scoring import score_resume_for_jd


def process_batch_resumes(
    file_bytes_list: List[bytes], 
    jd_text: str,
    filenames: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Core batch processing engine
    
    Args:
        file_bytes_list: List of PDF bytes
        jd_text: Job description text
        filenames: Optional list of original filenames
    
    Returns:
        Ranked results sorted by overall_score (descending)
    """
    results = []
    
    for i, file_bytes in enumerate(file_bytes_list):
        filename = filenames[i] if filenames else f"resume_{i+1}.pdf"
        
        # Pipeline: Extract → Parse → Score
        text = extract_text_from_bytes(file_bytes)
        parsed = parse_resume_text(text)
        score = score_resume_for_jd(parsed, jd_text)
        
        results.append({
            "filename": filename,
            "parsed": parsed.model_dump(),
            "score": score.model_dump(),
            "overall_score": score.overall_score
        })
    
    # Sort by score (highest first)
    return sorted(results, key=lambda x: x["overall_score"], reverse=True)


def save_batch_results(results: List[Dict], output_path: str = "batch_results.json"):
    """Save ranked results to JSON"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(results)} results to {output_path}")
