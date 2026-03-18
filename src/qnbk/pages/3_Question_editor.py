r"""Streamlit Question File Editor

Loads question files in the following format (YAML front-matter + body),
lets you edit metadata, question, options and solution, and save back to the same file
or to a new filename.

Example input file:
---
topic: Differentiation
difficulty: Easy
answer:
prev_year:
chapter: 1
---


What is the derivative of \(x^2\)?


OptionA: \(x\)
OptionB: \(2x\)
OptionC: \(x^3/3\)
OptionD: 2


## Solution

Differentiate: \(f'(x)=2x\).

Usage: `streamlit run streamlit_question_editor.py`

Notes:
- If you upload a file using the uploader, you can save it back to disk (if running locally) or
download the updated file.
- If you provide a file path that exists on the server where Streamlit runs, the app can overwrite that file when
you press "Save to same file".

"""

import re
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from qnbk import DEFAULT_QUESTIONS_DIR

st.set_page_config(page_title="Question File Editor", layout="wide")

# ----------------- Parsing Utilities -----------------

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
OPTION_RE = re.compile(r"^Option([A-Z]):\s*(.*)$", re.MULTILINE)
SOLUTION_HEADER_RE = re.compile(r"^##\s*Solution\s*$", re.IGNORECASE | re.MULTILINE)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, rest_text). Simple YAML-like parser: key: value per line."""
    m = FRONT_MATTER_RE.match(text)
    meta = {}
    rest = text
    if m:
        fm = m.group(1)
        rest = text[m.end() :]
        for line in fm.splitlines():
            if not line.strip():
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
            else:
                # treat whole line as key with empty value
                meta[line.strip()] = ""
    return meta, rest.lstrip("\n")


def parse_body(text: str) -> tuple[str, dict, str]:
    """Return (question_text, options_dict, solution_text)

    - Options matched by lines starting with OptionX: <text>
    - Solution is everything after a '## Solution' header (case-insensitive)
    - Question text is what's before the first Option or the solution header
    """
    # split solution
    sol_m = SOLUTION_HEADER_RE.search(text)
    solution = ""
    body_before_solution = text
    if sol_m:
        solution = text[sol_m.end() :].strip()
        body_before_solution = text[: sol_m.start()].rstrip()

    # find options
    options = {}
    for m in OPTION_RE.finditer(body_before_solution):
        idx = m.group(1)
        val = m.group(2).strip()
        options[idx] = val

    # question text = body_before_solution, but remove option lines
    question_lines = []
    for line in body_before_solution.splitlines():
        if OPTION_RE.match(line):
            continue
        question_lines.append(line)
    question = "\n".join(question_lines).strip()
    return question, options, solution


def compose_file(meta: dict, question: str, options: dict, solution: str) -> str:
    """Compose the file

    :param meta:
    :param question:
    :param options:
    :param solution:
    :return:
    """
    lines = ["---"]
    # keep the keys in the order of meta insertion where possible
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---\n")

    # body
    if question:
        lines.append(question.strip() + "\n")
    for key in sorted(options.keys()):
        lines.append(f"Option{key}: {options[key]}")
    if solution is not None and solution.strip() != "":
        lines.append("\n## Solution\n\n" + solution.strip())
    return "\n".join(lines)


# ----------------- UI -----------------

st.title("Question file editor")
st.markdown(
    "Load a question file (YAML front-matter + body), edit metadata, question, options and solution, then save back."
)

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Load")
    questions_root = Path(
        st.text_input("Question bank root directory", value=str(DEFAULT_QUESTIONS_DIR), placeholder="questions_output")
    )
    file_path = st.text_input(
        "Question file path (absolute or relative to root)",
        value="",
        placeholder="Differentiation/q_00001.md",
    )
    if file_path:
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            resolved_path = questions_root / resolved_path
        display_name = str(resolved_path)
        try:
            with open(resolved_path, encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            raw = ""
            st.error(f"Could not read {resolved_path}: {e}")
    else:
        raw = ""
        display_name = ""

    if not raw:
        st.info("Upload a file or provide a readable path to begin.")

with col2:
    st.header("Actions")
    save_name = st.text_input(
        "Save as path (absolute or relative to root; blank uses loaded file)",
        value=display_name.replace(str(questions_root) + "/", ""),
    )
    overwrite = st.checkbox("Overwrite the provided file path (if valid)", value=False)
    save_button = st.button("Save / Update file")

# If we have content, parse it and show editable fields
if raw:
    meta, rest = parse_front_matter(raw)
    question_text, options_dict, solution_text = parse_body(rest)

    st.subheader("Metadata")
    # show all existing keys; let user add new key
    meta_keys = list(meta.keys())
    edited_meta = {}
    for k in meta_keys:
        edited_meta[k] = st.text_input(f"{k}", value=meta.get(k, ""), key=f"meta_{k}")
    # allow adding a new metadata key
    new_key = st.text_input("Add new metadata key name (leave blank to skip)", value="", key="new_meta_key")
    if new_key.strip():
        new_val = st.text_input(f"Value for {new_key}", value="", key=f"meta_new_{new_key}")
        if new_key not in edited_meta:
            edited_meta[new_key] = new_val

    st.subheader("Question & Options")
    q_edit = st.text_area("Question text (Markdown / LaTeX allowed)", value=question_text, height=160)

    # ensure options A-D are present in UI even if missing
    option_keys = sorted(options_dict.keys())
    # default to A,B,C,D if no options found
    if not option_keys:
        option_keys = ["A", "B", "C", "D"]

    opt_cols = st.columns(len(option_keys))
    updated_options = {}
    for i, k in enumerate(option_keys):
        with opt_cols[i]:
            updated_options[k] = st.text_input(f"Option {k}", value=options_dict.get(k, ""), key=f"opt_{k}")

    st.subheader("Solution")
    sol_edit = st.text_area("Solution (markdown / LaTeX allowed)", value=solution_text, height=160)

    st.markdown("---")

    # compose content
    # merge metadata; keep user-edited values
    final_meta = edited_meta
    final_question = q_edit
    final_options = updated_options
    final_solution = sol_edit

    new_content = compose_file(final_meta, final_question, final_options, final_solution)

    st.subheader("Preview")
    st.code(new_content[:10000], language="text")

    # save logic
    if save_button:
        target_name = (
            save_name.strip()
            or display_name
            or (f"question_{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}.md")
        )
        target_path = Path(target_name) if target_name else None
        if target_path and not target_path.is_absolute():
            target_path = questions_root / target_path
        # if user requested overwrite and provided a server-side path
        saved = False
        save_errors = []
        if overwrite and file_path:
            try:
                with open(display_name, "w", encoding="utf-8") as f:
                    f.write(new_content)
                saved = True
                st.success(f"Overwrote file: {display_name}")
            except Exception as e:
                save_errors.append(f"Could not overwrite {display_name}: {e}")
        # else attempt to save to the selected path
        if not saved and target_path:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                saved = True
                st.success(f"Saved to: {target_path}")
            except Exception as e:
                save_errors.append(f"Could not save to {target_path}: {e}")

        if not saved:
            # provide as download
            b = new_content.encode("utf-8")
            st.download_button("Download updated file", data=b, file_name=target_name, mime="text/plain")
            if save_errors:
                for e in save_errors:
                    st.error(e)
            else:
                st.info("No writable path specified; use the download button above to get the updated file.")

    else:
        # quick download if user wants
        st.download_button(
            "Download current preview",
            data=new_content.encode("utf-8"),
            file_name=(save_name or display_name or "question.md"),
            mime="text/plain",
        )

else:
    st.stop()

# ----------------- End -----------------
