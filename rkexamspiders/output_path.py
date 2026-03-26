import re
from pathlib import Path


def safe_path_segment(value, default: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]+', "_", str(value)).strip()
    return safe or default


def build_output_file_path(
    *,
    subject_name=None,
    subject_path=None,
    paper_type_name=None,
    paper_type=None,
    paper_name=None,
    paper_id=None,
    output_dir: str | Path = "output",
) -> Path:
    subject = subject_name or subject_path or "unknown_subject"
    paper_type_value = paper_type_name or paper_type or "unknown_type"
    paper = paper_name if paper_name else paper_id

    safe_subject = safe_path_segment(subject, "unknown_subject")
    safe_type = safe_path_segment(paper_type_value, "unknown_type")
    safe_paper = safe_path_segment(paper, "unknown")

    return Path(output_dir) / safe_subject / safe_type / f"{safe_paper}.json"