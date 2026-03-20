"""Utility functions"""

import re
from pathlib import Path

import yaml
from loguru import logger

option_pattern_raw = r"^\s*Option([A-D])\s*[:\-]?\s*(.+)"
opt_pattern = re.compile(option_pattern_raw, re.M)
opt_pattern_bare = re.compile(r"^\s*([A-D])[\.\)]\s*(.+)", re.M)


def write_md_file(qdict: dict, filename: str) -> None:
    """Write the question dictionary to a Markdown file with YAML front matter for metadata and body content below.

    :param qdict:
    :param filename:
    :return:
    """
    with open(filename, "w", encoding="utf-8") as f:
        # write metadata:
        f.write("---\n")
        for k, v in qdict["metadata"].items():
            f.write(f"{k}: {v}\n")
        f.write("---\n\n\n")
        # write question
        f.write(qdict["body"]["question"] + "\n\n")
        # write options if they exist
        options = qdict["body"]["options"]
        if len(options):
            for opt_label, opt in options.items():
                f.write(f"Option{opt_label}: {opt}\n")
        # write solution
        if qdict["body"]["solution"]:
            f.write("\n\n## Solution\n\n")
            f.write(qdict["body"]["solution"] + "\n")
    logger.info(f"Written to file: {filename}")


def split_solution_from_body(body: str) -> tuple[str, str]:
    """Separate solution section from the main body, if it exists.

    Look for a line that starts with "Solution"
    (optionally preceded by up to 3 # for headers, and followed by optional : or -), and split the body
    into question part and solution part.

    :param body:
    :return:
    """
    if not body:
        return body, ""
    lines = body.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        m = re.match(r"^\s*(#{1,3}\s*)?Solution\b\s*[:\-]?\s*(.*)$", line, re.IGNORECASE)
        if m:
            first_line_content = m.group(2) or ""
            rest = "".join(lines[idx + 1 :])
            solution = (first_line_content + ("\n" + rest if rest else "")).lstrip()
            return "".join(lines[:idx]), solution
    return body, ""


def read_question_file(path: Path, qns_dir: Path = "data") -> dict:
    """Get metadata, question, options and solution from a question file.

    Expects a Markdown file with YAML frontmatter for metadata, and the body containing the question text, options,
    and solution.
    @:param path: Path to the question Markdown file.
    """
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        msg = f"No YAML frontmatter found in {path}"
        raise ValueError(msg)
    meta_raw, body = m.group(1), m.group(2)
    meta = yaml.safe_load(meta_raw)
    if not meta:
        meta = {}
    # Have default values for all the required metadata fields.
    meta.setdefault("topic", "Uncategorized")
    meta.setdefault("difficulty", "Unknown")
    meta.setdefault("answer", None)
    meta.setdefault("class", "Unknown")
    meta.setdefault("last_used", "")
    meta.setdefault("prev_year", "")

    body = body.rstrip("\n")
    body_without_solution, extracted_solution = split_solution_from_body(body)
    yaml_solution = meta.pop("solution", None)
    solution_text = extracted_solution if extracted_solution and extracted_solution.strip() else (yaml_solution or "")

    options = {}
    # See if the options are named `OptionA: ...` etc. If not, try the bare format `A. ...` or `A) ...`
    for m_opt in opt_pattern.finditer(body_without_solution):
        letter = m_opt.group(1).upper()
        text_opt = m_opt.group(2).strip()
        options[letter] = text_opt
    if not options:
        for m in opt_pattern_bare.finditer(body_without_solution):
            options[m.group(1).upper()] = m.group(2).strip()
    split_opt = re.split(option_pattern_raw, body_without_solution, maxsplit=1, flags=re.M)
    question_text = split_opt[0].strip() if split_opt else body_without_solution.strip()

    return {
        "path": path,
        "meta": meta,
        "body": body_without_solution.strip(),
        "solution": solution_text.strip(),
        "question_text": question_text,
        "options": options,
        "filename": path.name,
        "relpath": str(path.relative_to(qns_dir)) if qns_dir in path.parents or path == qns_dir else str(path),
    }
