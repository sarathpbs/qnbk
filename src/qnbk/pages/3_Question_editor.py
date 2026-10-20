r"""Streamlit Question File Editor

Loads question files in the following format (YAML front-matter + body),
lets you edit metadata, question, options and solution, and save back to the same file
or to a new filename.
"""

from datetime import datetime, timezone
from pathlib import Path
import re

from loguru import logger
import streamlit as st

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.question_index import upsert_question
from qnbk.styles import inject_custom_css
from qnbk.utils import render_question_preview, syntax_help_panel

st.set_page_config(
    page_title="Question File Editor",
    page_icon="✏️",
    layout="wide",
)

inject_custom_css()

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
                meta[line.strip()] = ""
    return meta, rest.lstrip("\n")


def parse_body(text: str) -> tuple[str, dict, str]:
    """Return (question_text, options_dict, solution_text)."""
    sol_m = SOLUTION_HEADER_RE.search(text)
    solution = ""
    body_before_solution = text
    if sol_m:
        solution = text[sol_m.end() :].strip()
        body_before_solution = text[: sol_m.start()].rstrip()

    options = {}
    for m in OPTION_RE.finditer(body_before_solution):
        idx = m.group(1)
        val = m.group(2).strip()
        options[idx] = val

    question_lines = []
    for line in body_before_solution.splitlines():
        if OPTION_RE.match(line):
            continue
        question_lines.append(line)
    question = "\n".join(question_lines).strip()
    return question, options, solution


def compose_file(meta: dict, question: str, options: dict, solution: str) -> str:
    """Compose the file contents from parts."""
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---\n")

    if question:
        lines.append(question.strip() + "\n")
    for key in sorted(options.keys()):
        lines.append(f"Option{key}: {options[key]}")
    if solution is not None and solution.strip() != "":
        lines.append("\n## Solution\n\n" + solution.strip())
    return "\n".join(lines)


# ----------------- UI -----------------
st.title("Question File Editor ✏️")
st.caption("Load an existing question Markdown file, update metadata or formulas, and save back with immediate index synchronization.")

col1, col2 = st.columns([7, 3], gap="medium")

with col1:
    st.subheader("📂 Load Question")
    questions_root = Path(
        st.text_input("Question bank root directory", value=str(DEFAULT_QUESTIONS_DIR))
    )
    file_path = st.text_input(
        "Question file path (relative to root or absolute)",
        placeholder="Class-XI/Differentiation/q_00001.md",
    )
    raw = ""
    display_name = ""
    if file_path:
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            resolved_path = questions_root / resolved_path
        display_name = str(resolved_path)
        try:
            with open(resolved_path, encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            st.error(f"Could not read {resolved_path}: {e}")

    if not raw:
        st.info("💡 Enter a file path above to begin editing.")

with col2:
    st.subheader("⚙️ Save Options")
    default_save_val = display_name.replace(str(questions_root) + "/", "") if display_name else ""
    save_name = st.text_input(
        "Target save path (blank = overwrite loaded file)",
        value=default_save_val,
    )
    overwrite = st.checkbox("Allow overwriting existing target", value=True)
    save_button = st.button("💾 Save Changes", type="primary", use_container_width=True, disabled=not bool(raw))

if raw:
    meta, rest = parse_front_matter(raw)
    meta.setdefault("source", "")
    question_text, options_dict, solution_text = parse_body(rest)

    st.write("---")
    st.subheader("1. Metadata Attributes")

    meta_keys = list(meta.keys())
    edited_meta = {}

    m_cols = st.columns(3)
    col_idx = 0
    for k in meta_keys:
        if k == "difficulty":
            with m_cols[col_idx % 3]:
                difficulty_options = ["Easy", "Medium", "Hard"]
                loaded_diff = meta.get("difficulty", "Medium")
                curr_diff = loaded_diff if loaded_diff in difficulty_options else "Medium"
                edited_meta[k] = st.pills("Difficulty", difficulty_options, default=curr_diff)
        else:
            with m_cols[col_idx % 3]:
                edited_meta[k] = st.text_input(f"{k.capitalize()}", value=meta.get(k, ""), key=f"meta_{k}")
        col_idx += 1

    st.write("---")
    edit_left, edit_right = st.columns([1, 1], gap="large")

    with edit_left:
        st.subheader("2. Question Body & Options")
        q_edit = st.text_area("Question statement", value=question_text, height=180)

        option_keys = sorted(options_dict.keys())
        if not option_keys:
            option_keys = ["A", "B", "C", "D"]

        st.markdown("**Options:**")
        opt_cols = st.columns(2)
        updated_options = {}
        for i, k in enumerate(option_keys):
            with opt_cols[i % 2]:
                updated_options[k] = st.text_input(f"Option {k}", value=options_dict.get(k, ""), key=f"opt_{k}")

        if not any(updated_options.values()):
            updated_options = {}

        st.subheader("3. Solution Explanation")
        sol_edit = st.text_area("Detailed solution", value=solution_text, height=160)

    # compose content
    final_meta = edited_meta
    final_question = q_edit
    final_options = updated_options
    final_solution = sol_edit
    new_content = compose_file(final_meta, final_question, final_options, final_solution)

    # preview markdown
    preview_md = f"### Question\n\n{final_question}\n\n"
    non_empty_opts = {k: v for k, v in final_options.items() if v.strip()}
    if non_empty_opts:
        preview_md += "#### Options\n"
        for label in ["A", "B", "C", "D"]:
            opt_val = final_options.get(label, "")
            if opt_val.strip():
                preview_md += f"* **Option {label}**: {opt_val}\n"
    if final_solution.strip():
        preview_md += f"\n\n#### Solution\n{final_solution}"

    with edit_right:
        st.subheader("Live Rendered Preview")
        tab_preview, tab_raw, tab_guide = st.tabs(["👁️ Rendered Preview", "📝 Raw Markdown", "📖 Writing Guide"])
        with tab_preview:
            render_question_preview(preview_md, height=520)
        with tab_raw:
            st.code(new_content[:10000], language="markdown")
        with tab_guide:
            syntax_help_panel()

    # Save logic
    if save_button:
        target_name = (
            save_name.strip()
            or display_name
            or (f"question_{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}.md")
        )
        target_path = Path(target_name)
        if not target_path.is_absolute():
            target_path = questions_root / target_path

        saved = False
        save_errors = []
        if overwrite and file_path and str(target_path) == display_name:
            try:
                with open(display_name, "w", encoding="utf-8") as f:
                    f.write(new_content)
                saved = True
                st.success(f"✅ Successfully updated file: `{display_name}`")
            except Exception as e:
                save_errors.append(f"Could not write to {display_name}: {e}")
        else:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                saved = True
                st.success(f"✅ Saved new file: `{target_path}`")
            except Exception as e:
                save_errors.append(f"Could not save to {target_path}: {e}")

        if saved:
            actual_saved_path = target_path
            try:
                upsert_question(
                    {
                        "meta": final_meta,
                        "question_text": final_question,
                        "options": final_options,
                        "solution": final_solution,
                        "body": final_question,
                    },
                    file_path=actual_saved_path,
                    qdir=questions_root,
                )
                st.info("🔄 SQLite search index automatically synchronized.")
            except Exception as e_idx:
                logger.warning(f"Could not update index for {actual_saved_path}: {e_idx}")

        if not saved:
            b = new_content.encode("utf-8")
            st.download_button("📥 Download Updated File", data=b, file_name=target_path.name, mime="text/plain")
            for e in save_errors:
                st.error(e)
else:
    st.stop()
